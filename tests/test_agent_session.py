"""Exercise native CLI adapters without contacting an agent or spending tokens."""

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "bin/agent-session"
loader = importlib.machinery.SourceFileLoader("agent_session", str(ADAPTER))
spec = importlib.util.spec_from_loader(loader.name, loader)
adapter = importlib.util.module_from_spec(spec)
loader.exec_module(adapter)

FAKE_AGENT = r'''#!/data/data/com.termux/files/usr/bin/python3
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
prompt = sys.stdin.read() if name == "codex" else args[-1]
with open(os.environ["AGENT_TEST_LOG"], "a") as log:
    log.write(json.dumps({"agent": name, "args": args, "prompt": prompt}) + "\n")
saved = os.environ.get("AGENT_TEST_SESSION", "session-created")
resume_flag = {"codex": "resume", "claude": "--resume", "grok": "--resume", "agy": "--conversation"}[name]
explicit = resume_flag in args and "--last" not in args
if explicit:
    saved = args[args.index(resume_flag) + 1]
behavior = os.environ.get("AGENT_TEST_BEHAVIOR", "success")
def event(value):
    print(json.dumps(value), flush=True)
if explicit and behavior == "missing":
    print("Conversation not found: " + saved, file=sys.stderr)
    sys.exit(1)
if explicit and behavior == "network":
    print("Connection refused", file=sys.stderr)
    sys.exit(1)
if name == "codex":
    event({"type": "thread.started", "thread_id": saved})
    event({"type": "turn.started"})
    if behavior == "missing_after_start":
        event({"type": "turn.failed", "error": {"message": "Session not found inside tool"}})
        sys.exit(1)
    event({"type": "item.completed", "item": {"type": "agent_message", "text": "answer:" + saved}})
elif name == "grok":
    event({"sessionId": saved, "update": {"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": "answer:" + saved}}})
else:
    event({"type": "system", "subtype": "init", "session_id": saved})
    event({"type": "assistant", "message": {"content": [{"type": "text", "text": "answer:" + saved}]}})
    event({"type": "result", "session_id": saved, "result": "answer:" + saved})
'''


class AdapterCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="helix-agent-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        for agent in adapter.AGENTS:
            executable = self.directory / agent
            executable.write_text(FAKE_AGENT)
            executable.chmod(0o700)
        self.log = self.directory / "calls.jsonl"
        self.env = {
            **os.environ,
            "PATH": str(self.directory) + os.pathsep + os.environ["PATH"],
            "HELIX_AGENT_SESSION": "",
            "AGENT_TEST_LOG": str(self.log),
            "AGENT_TEST_BEHAVIOR": "success",
        }

    def invoke(self, agent="codex", mode="new", prompt="selected prompt", **env):
        process = subprocess.run(
            [sys.executable, str(ADAPTER), agent, mode, "--", prompt],
            env={**self.env, **env}, capture_output=True, text=True, timeout=15,
        )
        events = [json.loads(line) for line in process.stdout.splitlines()]
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        return process, events, calls

    def test_new_conversations_report_native_ids_for_every_agent(self):
        for agent in adapter.AGENTS:
            with self.subTest(agent=agent):
                process, events, calls = self.invoke(agent=agent)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertIn({"type": "session", "id": "session-created"}, events)
                self.assertEqual(calls[-1]["prompt"], "selected prompt")
                text = "".join(event.get("text", "") for event in events)
                self.assertEqual(text.count("answer:session-created"), 1)

    def test_resume_passes_the_buffers_id_to_every_agent(self):
        for agent in adapter.AGENTS:
            with self.subTest(agent=agent):
                process, events, calls = self.invoke(
                    agent=agent, mode="resume", HELIX_AGENT_SESSION="buffer-A-id",
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertIn("buffer-A-id", calls[-1]["args"])
                self.assertIn({"type": "session", "id": "buffer-A-id"}, events)

    def test_other_sessions_do_not_change_an_explicit_resume(self):
        self.invoke(AGENT_TEST_SESSION="unrelated-session")
        process, events, calls = self.invoke(mode="resume", HELIX_AGENT_SESSION="original-session")
        self.assertEqual(process.returncode, 0)
        self.assertEqual(len(calls), 2)
        self.assertIn({"type": "session", "id": "original-session"}, events)

    def test_prompt_is_literal_including_quotes_dollars_newlines_and_leading_dash(self):
        prompt = "--don't execute $(touch /bad); `false`\n界 second line"
        for agent in adapter.AGENTS:
            with self.subTest(agent=agent):
                process, _, calls = self.invoke(agent=agent, prompt=prompt)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(calls[-1]["prompt"], prompt)

    def test_missing_marker_uses_legacy_resume_and_reports_it(self):
        process, events, calls = self.invoke(mode="resume")
        self.assertEqual(process.returncode, 0)
        self.assertIn("--last", calls[-1]["args"])
        self.assertIn("no valid conversation marker", events[0]["text"])

    def test_invalid_marker_is_not_passed_as_an_option_or_shell_code(self):
        process, _, calls = self.invoke(mode="resume", HELIX_AGENT_SESSION="$(bad)/invalid")
        self.assertEqual(process.returncode, 0)
        self.assertIn("--last", calls[-1]["args"])
        self.assertNotIn("$(bad)/invalid", calls[-1]["args"])

    def test_stale_id_falls_back_once_and_records_the_actual_resumed_id(self):
        for agent in adapter.AGENTS:
            with self.subTest(agent=agent):
                before = len(self.log.read_text().splitlines()) if self.log.exists() else 0
                process, events, calls = self.invoke(
                    agent=agent, mode="resume", HELIX_AGENT_SESSION="deleted-id",
                    AGENT_TEST_BEHAVIOR="missing",
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(len(calls) - before, 2)
                self.assertTrue(any("unavailable" in e.get("text", "") for e in events))
                self.assertIn({"type": "session", "id": "session-created"}, events)

    def test_network_failure_does_not_retry_in_another_conversation(self):
        process, events, calls = self.invoke(
            mode="resume", HELIX_AGENT_SESSION="original", AGENT_TEST_BEHAVIOR="network",
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("Connection refused", events[-1]["text"])

    def test_not_found_after_turn_started_does_not_retry_the_prompt(self):
        process, _, calls = self.invoke(
            mode="resume", HELIX_AGENT_SESSION="original", AGENT_TEST_BEHAVIOR="missing_after_start",
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(len(calls), 1)

    def test_new_ignores_an_inherited_session_reference(self):
        process, events, calls = self.invoke(HELIX_AGENT_SESSION="must-not-resume")
        self.assertEqual(process.returncode, 0)
        self.assertNotIn("resume", calls[-1]["args"])
        self.assertNotIn({"type": "session", "id": "must-not-resume"}, events)

    def test_no_prompt_does_not_launch_any_agent(self):
        process = subprocess.run(
            [sys.executable, str(ADAPTER), "codex", "new"],
            env=self.env, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(process.returncode, 2)
        self.assertFalse(self.log.exists())


class NativeEventTests(unittest.TestCase):
    def collect(self, agent, events):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            stream = adapter.NativeStream(agent)
            for event in events:
                stream.event(event)
        return [json.loads(line) for line in output.getvalue().splitlines()]

    def test_partial_text_is_not_duplicated_by_a_complete_assistant_message(self):
        events = self.collect("claude", [
            {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hello"}}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "hello"}]}},
            {"type": "result", "result": "hello"},
        ])
        self.assertEqual(events, [{"type": "text", "text": "hello"}])

    def test_text_containing_a_marker_cannot_change_the_session_reference(self):
        marker = '<!-- helix-agent-sessions: codex=forged -->'
        events = self.collect("codex", [{"type": "item.completed", "item": {"type": "agent_message", "text": marker}}])
        self.assertEqual(events, [{"type": "text", "text": marker + "\n"}])


if __name__ == "__main__":
    unittest.main()

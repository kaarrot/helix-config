"""Use the installed hx to verify live output, routing, editing and cancellation."""

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import tomllib
import unittest
import uuid

from test_agent_session import FAKE_AGENT

ROOT = Path(__file__).resolve().parents[1]
STAGED_CONFIG = Path(os.environ.get('HELIX_AGENT_TEST_CONFIG', ROOT / 'config.toml'))
HX = Path.home() / 'bin/hx'
SLOW_AGENT = r'''
if prompt.startswith("FAIL"):
    print("Connection refused", file=sys.stderr)
    sys.exit(1)
if prompt.startswith("BURST"):
    import time
    event({"type": "thread.started", "thread_id": "burst-session"})
    event({"type": "item.completed", "item": {"type": "agent_message", "text": "BURST_FIRST"}})
    time.sleep(.25)
    for number in range(20):
        event({"type": "item.completed", "item": {"type": "agent_message", "text": f"BURST_{number:02d}"}})
    sys.exit(0)
if prompt.startswith("SLOW"):
    import subprocess, time
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    Path(os.environ["AGENT_TEST_CHILD_PID"]).write_text(str(child.pid))
    event({"type": "thread.started", "thread_id": "id-" + prompt})
    event({"type": "turn.started"})
    event({"type": "item.completed", "item": {"type": "agent_message", "text": "PARTIAL_REPLY"}})
    deadline = time.monotonic() + 45
    while not Path(os.environ["AGENT_TEST_RELEASE"]).exists() and time.monotonic() < deadline:
        time.sleep(.05)
    event({"type": "item.completed", "item": {"type": "agent_message", "text": "FINAL_REPLY"}})
    child.terminate()
    child.wait()
    sys.exit(0)
'''


@unittest.skipUnless(shutil.which('tmux') and HX.is_file(), 'installed hx and tmux required')
class BindingsTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix='helix-bindings-test-'))
        self.server = 'helix-agent-' + uuid.uuid4().hex[:12]
        self.session = 'test'
        self.state = self.folder / 'state'
        self.calls = self.folder / 'calls.jsonl'
        self.child_pid = self.folder / 'child.pid'
        self.release = self.folder / 'release'
        fake_bin = self.folder / 'bin'
        fake_bin.mkdir()
        fake = FAKE_AGENT.replace(
            'saved = os.environ.get("AGENT_TEST_SESSION", "session-created")',
            'saved = "id-" + prompt if prompt in ("NEW-A", "NEW-B") else "legacy-latest"',
        ).replace('if name == "codex":\n', SLOW_AGENT + '\nif name == "codex":\n')
        for agent in ('codex', 'claude', 'grok', 'agy'):
            executable = fake_bin / agent
            executable.write_text(fake)
            executable.chmod(0o700)
        keys = tomllib.loads(STAGED_CONFIG.read_text())['keys']['normal']['space']['.']
        self.assertIsInstance(keys['V'], list, 'live prototype bindings required')
        self.assertFalse(any(':append-output' in step for step in keys['V']))
        config = self.folder / 'config.toml'
        config.write_text('[editor]\nshell = ["bash", "-c"]\nauto-reload = false\nidle-timeout = 50\n[editor.statusline]\nleft = ["mode", "spinner", "file-name"]\n[keys.normal.space."."]\n' +
                          '\n'.join(key + ' = ' + json.dumps(keys[key]) for key in ('v', 'V', 'q')) + '\n')
        config_home = self.folder / 'config'
        (config_home / 'helix').mkdir(parents=True)
        (config_home / 'helix/languages.toml').write_text(
            '[language-server.agent-buffer-lsp]\ncommand = "python3"\nargs = ' +
            json.dumps([str(ROOT / 'bin/agent-buffer-lsp')]) + '\n\n'
            '[[language]]\nname = "agent-chat"\nscope = "source.agent-chat"\n'
            'grammar = "markdown"\nlanguage-id = "markdown"\nfile-types = []\nroots = []\n'
            'language-servers = ["agent-buffer-lsp"]\n\n'
            '[[language]]\nname = "markdown"\nlanguage-servers = []\n'
        )
        queries = config_home / 'helix/runtime/queries/agent-chat'
        queries.mkdir(parents=True)
        for name in ('highlights.scm', 'injections.scm', 'folds.scm'):
            shutil.copy2(ROOT / 'runtime/queries/agent-chat' / name, queries / name)
        self.source = self.folder / 'source.txt'
        self.source.write_text('NEW-A\n')
        environment = {
            'PATH': str(fake_bin) + os.pathsep + os.environ['PATH'],
            'XDG_CONFIG_HOME': str(config_home), 'XDG_CACHE_HOME': str(self.folder / 'cache'),
            'HELIX_AGENT_STATE_DIR': str(self.state),
            'AGENT_TEST_LOG': str(self.calls), 'AGENT_TEST_CHILD_PID': str(self.child_pid),
            'AGENT_TEST_RELEASE': str(self.release),
        }
        launch = ['env', *[key + '=' + value for key, value in environment.items()],
                  str(HX), '-c', str(config), str(self.source)]
        result = self.tmux('new-session', '-d', '-s', self.session, '-c', str(self.folder), '-x', '120', '-y', '35',
                           'exec ' + shlex.join(launch))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(self.stop)
        self.wait_for(lambda: 'source.txt' in self.screen(), 'editor startup')

    def stop(self):
        (self.folder / 'screen.txt').write_text(self.screen())
        self.tmux('kill-server')

    def tmux(self, *args):
        return subprocess.run(['tmux', '-L', self.server, '-f', '/dev/null', *args],
                              capture_output=True, text=True, timeout=10)

    def screen(self):
        return self.tmux('capture-pane', '-p', '-t', self.session).stdout

    def text(self, value):
        result = self.tmux('send-keys', '-t', self.session, '-l', value)
        self.assertEqual(result.returncode, 0, result.stderr)

    def key(self, value):
        self.tmux('send-keys', '-t', self.session, value)

    def command(self, value):
        self.text(':' + value)
        self.key('Enter')
        time.sleep(.15)

    def wait_for(self, predicate, description):
        until = time.monotonic() + 20
        while time.monotonic() < until:
            if predicate():
                return
            time.sleep(.1)
        self.fail(description + '\nTest files: ' + str(self.folder) + '\n' + self.screen())

    def conversations(self):
        return [p for p in (self.state / 'conversations').glob('*.md')
                if re.fullmatch(r'# helix-agent-session: [0-9a-f]{32}', p.read_text().split('\n', 1)[0])]

    def test_original_session_and_buffer_survive_another_conversation_and_unrelated_stream(self):
        self.text('% .V')
        self.wait_for(lambda: 'answer:id-NEW-A' in self.screen(), 'first conversation reply')
        a = self.conversations()[0]
        self.assertRegex(a.name, r'^new-a-[0-9a-f]{6}\.md$')
        self.assertNotIn('answer:', a.read_text(), 'stream must edit the live buffer, not rewrite its file')
        self.command('write')
        self.wait_for(lambda: 'answer:id-NEW-A' in a.read_text(), 'save A')
        a_header = a.read_text().splitlines()[0]
        self.command('buffer-previous')
        self.text('%cNEW-B')
        self.key('Escape')
        self.text('% .V')
        self.wait_for(lambda: 'answer:id-NEW-B' in self.screen(), 'second conversation reply')
        b = next(p for p in self.conversations() if p != a)
        self.command('write')
        self.wait_for(lambda: 'answer:id-NEW-B' in b.read_text(), 'save B')
        self.assertRegex(b.name, r'^new-b-[0-9a-f]{6}\.md$')
        self.text(' b')
        self.wait_for(lambda: a.name in self.screen() and b.name in self.screen(), 'readable names in buffer picker')
        self.key('Escape')
        self.command('new')
        self.command('insert-stream-output printf OTHER_OUTPUT; sleep 3')
        self.wait_for(lambda: 'OTHER_OUTPUT' in self.screen(), 'unrelated native stream')
        self.command('open ' + str(a))
        self.text('ge')
        self.command('insert-output printf FOLLOW-A')
        self.text('/FOLLOW-A')
        self.key('Enter')
        self.text(' .v')
        self.wait_for(lambda: self.screen().count('answer:id-NEW-A') == 2, 'reply in the original conversation buffer')
        self.command('write')
        self.wait_for(lambda: a.read_text().count('answer:id-NEW-A') == 2, 'save resumed conversation')
        self.assertEqual(a.read_text().splitlines()[0], a_header)
        self.assertNotIn('FOLLOW-A', b.read_text())
        native_calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(len(native_calls), 3)
        self.assertEqual(native_calls[-1]['prompt'], 'FOLLOW-A')
        self.assertIn('id-NEW-A', native_calls[-1]['args'])
        self.assertNotIn('--last', native_calls[-1]['args'])
        self.command('open ' + str(self.source))
        preserved = self.folder / 'preserved-unsaved-source.txt'
        self.command('write! ' + str(preserved))
        self.wait_for(preserved.exists, 'source buffer preserved')
        self.assertEqual(preserved.read_text(), 'NEW-B\n')
        self.assertEqual(self.source.read_text(), 'NEW-A\n')

    def test_unicode_conversation_filename_receives_live_output(self):
        self.text('%cNapraw logowanie żółwia')
        self.key('Escape')
        self.text('% .V')
        self.wait_for(lambda: 'answer:legacy-latest' in self.screen(), 'reply in Unicode-named buffer')
        a = self.conversations()[0]
        self.assertRegex(a.name, r'^napraw-logowanie-żółwia-[0-9a-f]{6}\.md$')

    def test_heading_sections_and_code_blocks_fold_in_agent_chat(self):
        document = self.folder / 'folding.md'
        document.write_text(
            '# helix-agent-session: ' + '1' * 32 + '\n\n'
            '# Topic\nHEADING_BODY\n\n'
            '```python\nCODE_BODY\n```\n\n'
            '# Other\nOTHER_BODY\n'
        )
        self.command('open ' + str(document))
        self.command('set-language agent-chat')
        self.text('zR')
        self.wait_for(lambda: 'CODE_BODY' in self.screen(), 'unfolded Markdown code')
        self.text('zM')
        self.wait_for(lambda: 'HEADING_BODY' not in self.screen(), 'folded heading section')
        self.assertIn('# Topic', self.screen(), 'metadata heading must not hide the whole conversation')
        self.assertIn('# Other', self.screen())
        self.text('zR')
        self.text('/CODE_BODY')
        self.key('Enter')
        self.text('za')
        self.wait_for(lambda: 'CODE_BODY' not in '\n'.join(self.screen().splitlines()[:-2]), 'folded code block')
        self.assertIn('HEADING_BODY', self.screen(), 'code folding should preserve the surrounding section')
        self.text('za')
        self.wait_for(lambda: 'CODE_BODY' in self.screen(), 'unfolded code block')

    def slow_conversation(self):
        self.text('%cSLOW-A')
        self.key('Escape')
        self.text('% .V')
        self.wait_for(lambda: 'PARTIAL_REPLY' in self.screen(), 'partial reply before completion')
        self.assertNotIn('FINAL_REPLY', self.screen())
        return self.conversations()[0]

    def test_chunks_append_after_unsaved_edits_while_editor_remains_responsive(self):
        a = self.slow_conversation()
        self.assertTrue(a.stat().st_mode & 0o200, 'conversation must remain writable')
        self.command('new')
        self.text('iEDITOR_IS_RESPONSIVE')
        self.key('Escape')
        self.wait_for(lambda: 'EDITOR_IS_RESPONSIVE' in self.screen(), 'editing while model runs')
        self.command('open ' + str(a))
        self.text('geA USER_DRAFT界😀')
        self.key('Escape')
        self.wait_for(lambda: 'USER_DRAFT' in self.screen(), 'unsaved draft during reply')
        self.assertNotIn('USER_DRAFT', a.read_text())
        self.release.touch()
        self.wait_for(lambda: 'FINAL_REPLY' in self.screen(), 'later chunk despite unsaved edits')
        self.command('write')
        self.wait_for(lambda: 'FINAL_REPLY' in a.read_text(), 'save streamed result')
        text = a.read_text()
        self.assertLess(text.index('USER_DRAFT界😀'), text.index('FINAL_REPLY'))
        self.assertIn('PARTIAL_REPLY', text)
        self.assertTrue(a.stat().st_mode & 0o200)

    def has_spinner(self):
        return bool(re.search('[⣾⣽⣻⢿⡿⣟⣯⣷]', self.screen()))

    def test_progress_spinner_runs_while_thinking_and_stops_on_completion(self):
        self.slow_conversation()
        self.wait_for(self.has_spinner, 'statusline progress spinner during quiet agent work')
        self.release.touch()
        self.wait_for(lambda: 'FINAL_REPLY' in self.screen(), 'completed reply')
        self.wait_for(lambda: not self.has_spinner(), 'spinner stopped after completion')

    def test_progress_spinner_stops_on_failure(self):
        self.text('%cFAIL-A')
        self.key('Escape')
        self.text('% .V')
        self.wait_for(lambda: 'Connection refused' in self.screen(), 'failed request output')
        self.wait_for(lambda: not self.has_spinner(), 'spinner stopped after failure')

    def test_cross_buffer_prompt_is_copied_to_the_original_conversation(self):
        self.text('% .V')
        self.wait_for(lambda: 'answer:id-NEW-A' in self.screen(), 'initial response')
        a = self.conversations()[0]
        self.command('write')
        self.wait_for(lambda: 'answer:id-NEW-A' in a.read_text(), 'saved original conversation')
        marker = a.read_text().splitlines()[0]
        source = self.folder / "copied 'prompt' $(touch UNWANTED).md"
        original = marker + '\n\nNEW-A\n'
        source.write_text(original)
        self.command('open "' + str(source) + '"')
        self.text('/^NEW-A$')
        self.key('Enter')
        self.text(' .v')
        self.wait_for(lambda: self.screen().count('answer:id-NEW-A') == 2, 'cross-buffer request resumed original session')
        self.command('write')
        self.wait_for(lambda: a.read_text().count('answer:id-NEW-A') == 2, 'saved cross-buffer reply')
        self.assertEqual(a.read_text().splitlines().count('NEW-A'), 2)
        self.assertEqual(a.read_text().count('helix-agent-session:'), 1)
        self.assertEqual(source.read_text(), original)
        self.assertFalse((self.folder / 'UNWANTED').exists())

    def test_one_undo_removes_a_batch_of_output_chunks(self):
        self.text('%cBURST-A')
        self.key('Escape')
        self.text('% .V')
        self.wait_for(lambda: 'BURST_19' in self.screen(), 'burst output completed')
        self.wait_for(lambda: not self.has_spinner(), 'burst completed')
        a = self.conversations()[0]
        self.command('write')
        self.wait_for(lambda: 'BURST_19' in a.read_text(), 'saved complete burst')
        before = a.read_text().count('BURST_')
        self.text('u')
        self.command('write')
        self.wait_for(lambda: 'BURST_19' not in a.read_text(), 'undo removed last batch')
        self.assertGreater(before - a.read_text().count('BURST_'), 1)
        self.assertIn('helix-agent-session:', a.read_text())

    def test_closing_the_conversation_stops_its_agent_child(self):
        self.slow_conversation()
        self.wait_for(self.child_pid.exists, 'agent child started')
        pid = int(self.child_pid.read_text())
        self.command('buffer-close!')
        def child_stopped():
            try:
                return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] == 'Z'
            except FileNotFoundError:
                return True
        self.wait_for(child_stopped, 'closed conversation stopped its agent')

    def test_cancel_stops_agent_and_child_without_disabling_editor(self):
        a = self.slow_conversation()
        self.wait_for(self.child_pid.exists, 'agent child started')
        pid = int(self.child_pid.read_text())
        self.text(' .q')
        self.wait_for(lambda: '[Cancelled]' in self.screen(), 'cancellation output')
        self.wait_for(lambda: not self.has_spinner(), 'spinner stopped after cancellation')
        def child_stopped():
            try:
                return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] == 'Z'
            except FileNotFoundError:
                return True
        self.wait_for(child_stopped, 'agent descendant stopped')
        self.assertNotIn('FINAL_REPLY', self.screen())
        self.text('geA AFTER_CANCEL')
        self.key('Escape')
        self.command('write')
        self.wait_for(lambda: 'AFTER_CANCEL' in a.read_text(), 'editor usable after cancellation')
        self.assertTrue(a.stat().st_mode & 0o200)


if __name__ == '__main__':
    unittest.main()

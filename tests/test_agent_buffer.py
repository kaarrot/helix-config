import json
import os
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_agent_session import FAKE_AGENT
from agent_lsp_client import Client

ROOT = Path(__file__).resolve().parents[1]
BUFFER = ROOT / 'bin/agent-buffer'


class BufferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='helix-buffer-test-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.state = self.directory / 'state'
        self.settings = self.directory / 'settings.json'
        self.settings.write_text('{}')
        fake = FAKE_AGENT.replace('name = Path(sys.argv[0]).name', 'os.environ.update(json.loads(Path(os.environ["AGENT_TEST_SETTINGS_FILE"]).read_text()))\nname = Path(sys.argv[0]).name')
        fake = fake.replace('{"agent": name, "args": args, "prompt": prompt}', '{"agent": name, "args": args, "prompt": prompt, "cwd": os.getcwd()}')
        burst = '''if behavior == "burst":
    import time
    event({"type": "thread.started", "thread_id": saved})
    for number in range(30):
        event({"type": "item.completed", "item": {"type": "agent_message", "text": f"BURST_{number:02d}"}})
        time.sleep(.01)
    sys.exit(0)
'''
        fake = fake.replace('if name == "codex":\n', burst + '\nif name == "codex":\n')
        for agent in ('codex', 'claude', 'grok', 'agy'):
            script = self.directory / agent
            script.write_text(fake)
            script.chmod(0o700)
        self.log = self.directory / 'calls.jsonl'
        self.env = {
            **os.environ, 'PATH': str(self.directory) + os.pathsep + os.environ['PATH'],
            'HELIX_AGENT_STATE_DIR': str(self.state), 'HELIX_AGENT_SCOPE': 'test-editor',
            'AGENT_TEST_LOG': str(self.log), 'AGENT_TEST_SESSION': 'session-A',
            'AGENT_TEST_SETTINGS_FILE': str(self.settings),
        }
        self.client = Client(self.env, cwd=self.directory)
        self.addCleanup(self.client.close)

    def command(self, *args, text='', **env):
        result = subprocess.run([sys.executable, str(BUFFER), *args], input=text,
                                env={**self.env, **env}, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def prepare(self, prompt, header='', agent='codex', mode='new', line=2, source=None):
        context = ['--buffer-context', 'capture; exit # helix-agent-buffer: ' + str(source)] if source else []
        self.command('capture', agent, mode, '--line-start', str(line), *context, text=prompt)
        self.command('header', text=header)
        path = Path(self.command('prepare').strip())
        self.client.open(path)
        return path

    def complete(self, path, **env):
        self.settings.write_text(json.dumps(env))
        uri = path.resolve().as_uri()
        before = self.client.documents[uri]['text']
        self.command('start')
        self.client.pump_until(lambda: 'answer:' in self.client.documents[uri]['text'][len(before):])
        result = self.client.documents[uri]['text']
        path.write_text(result)  # Simulate an explicit editor save in this fixture.
        return result[len(before):]

    def test_resume_keeps_original_conversation_file_after_another_session(self):
        a = self.prepare('First prompt\n')
        self.complete(a)
        a_header = a.read_text().splitlines()[0]
        b = self.prepare('Other prompt\n')
        self.complete(b, AGENT_TEST_SESSION='session-B')
        resumed = self.prepare('Follow A\n', a_header, mode='resume')
        self.assertEqual(resumed, a)
        response = self.complete(resumed)
        self.assertIn('answer:session-A', response)
        self.assertNotIn('Follow A', b.read_text())
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertIn('session-A', calls[-1]['args'])
        self.assertNotIn('--last', calls[-1]['args'])

    def test_hash_is_the_first_line_before_the_native_agent_runs(self):
        output = self.prepare('Selected source text\n')
        text = output.read_text()
        self.assertRegex(text.splitlines()[0], r'^# helix-agent-session: [0-9a-f]{32}$')
        self.assertEqual(output.name, f"selected-source-text-{text.splitlines()[0].split()[-1][:6]}.md")
        self.assertEqual(text.split('\n\n', 1)[1], 'Selected source text\n')
        self.assertFalse(self.log.exists())

    def test_filename_uses_the_first_nonempty_prompt_line_and_unicode(self):
        a = self.prepare('\n# Napraw logowanie żółwia!\nMore details here\n')
        token = a.read_text().splitlines()[0].split()[-1]
        self.assertEqual(a.name, f'napraw-logowanie-żółwia-{token[:6]}.md')
        self.assertLessEqual(len(a.name.encode('utf-8')), 255)

    def test_legacy_hash_filename_is_resumed_without_moving_it(self):
        token = '1' * 32
        directory = self.state / 'conversations'
        directory.mkdir(parents=True)
        legacy = directory / (token + '.md')
        marker = f'# helix-agent-session: {token}'
        original = marker + '\n\nExisting conversation\n'
        legacy.write_text(original)
        resumed = self.prepare('Follow this old conversation', marker, mode='resume')
        self.assertEqual(resumed, legacy)
        self.assertEqual(legacy.read_text(), original)
        self.assertEqual(list(directory.glob('*.md')), [legacy])

    def test_short_hash_collision_keeps_conversations_separate(self):
        directory = self.state / 'conversations'
        directory.mkdir(parents=True)
        first_token = '123456' + 'a' * 26
        second_token = '123456' + 'b' * 26
        first = directory / 'fix-login-bug-123456.md'
        original = f'# helix-agent-session: {first_token}\n\nFirst conversation\n'
        first.write_text(original)
        marker = f'# helix-agent-session: {second_token}'
        second = self.prepare('Fix login bug!', marker, mode='resume')
        self.assertEqual(second.name, 'fix-login-bug-123456bbbb.md')
        self.assertEqual(first.read_text(), original)
        self.assertEqual(second.read_text().splitlines()[0], marker)
        self.assertEqual(self.prepare('Different follow-up', marker, mode='resume'), second)

    def test_empty_slug_has_a_readable_fallback_and_long_titles_are_bounded(self):
        fallback = self.prepare('😀🦉')
        token = fallback.read_text().splitlines()[0].split()[-1]
        self.assertEqual(fallback.name, f'conversation-{token[:6]}.md')
        long_name = self.prepare('Long prompt title ' * 40)
        self.assertLessEqual(len(long_name.stem), 48 + 1 + 6)
        self.assertNotIn('--', long_name.name)

    def test_selected_metadata_is_removed_before_sending(self):
        a = self.prepare('Initial prompt\n')
        self.complete(a)
        header = a.read_text().splitlines()[0]
        self.prepare(header + '\nnew prompt\nsecond line\n', header, mode='resume', line=1)
        self.complete(a)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(calls[-1]['prompt'], 'new prompt\nsecond line')

    def test_quote_and_shell_text_are_passed_literally(self):
        prompt = "don't run $(touch /bad); `false`\n界\n"
        a = self.prepare(prompt)
        self.complete(a)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(calls[-1]['prompt'], prompt[:-1])

    def test_unmarked_resume_preserves_native_fallback(self):
        a = self.prepare('Follow legacy\n', mode='resume')
        response = self.complete(a)
        self.assertIn('no valid conversation marker', response)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertIn('--last', calls[-1]['args'])

    def test_stale_native_id_falls_back_and_updates_the_reference(self):
        a = self.prepare('Initial\n')
        self.complete(a)
        header = a.read_text().splitlines()[0]
        self.prepare('Follow\n', header, mode='resume')
        response = self.complete(a, AGENT_TEST_BEHAVIOR='missing', AGENT_TEST_SESSION='fallback-id')
        self.assertIn('saved conversation unavailable', response)
        token = header.split()[-1]
        ids = json.loads((self.state / 'registry' / (token + '.json')).read_text())
        self.assertEqual(ids['codex'], 'fallback-id')

    def test_agent_references_are_separate_in_the_same_conversation(self):
        a = self.prepare('Initial\n')
        self.complete(a)
        header = a.read_text().splitlines()[0]
        b = self.prepare('Ask Claude\n', header, mode='resume', agent='claude')
        self.assertEqual(a, b)
        self.complete(b, AGENT_TEST_SESSION='claude-id')
        ids = json.loads((self.state / 'registry' / (header.split()[-1] + '.json')).read_text())
        self.assertEqual(ids, {'codex': 'session-A', 'claude': 'claude-id'})

    def test_a_racing_user_edit_is_preserved_and_output_retries_at_the_new_end(self):
        a = self.prepare('Initial prompt\n')
        self.client.force_race = True
        self.complete(a)
        text = self.client.documents[a.resolve().as_uri()]['text']
        self.assertIn('UNSAVED_RACING_EDIT界😀', text)
        self.assertLess(text.index('UNSAVED_RACING_EDIT界😀'), text.index('answer:session-A'))
        self.assertGreaterEqual(self.client.rejected_edits, 1)

    def test_cancel_before_language_server_opens_the_document_does_not_launch(self):
        self.command('capture', 'codex', 'new', '--line-start', '2', text='Do not run')
        self.command('header', text='')
        a = Path(self.command('prepare').strip())
        self.command('start')
        self.command('cancel', text=a.read_text().splitlines()[0])
        self.client.open(a)
        self.assertEqual(list((self.state / 'queue/test-editor').glob('*.json')), [])
        self.assertFalse(self.log.exists())

    def test_cross_buffer_prompt_is_copied_even_if_it_appeared_earlier(self):
        a = self.prepare('Initial prompt')
        self.complete(a)
        marker = a.read_text().splitlines()[0]
        source = self.directory / 'copied-marker.md'
        original = marker + '\n\nInitial prompt\n'
        source.write_text(original)
        target = self.prepare('Initial prompt', marker, mode='resume', source=source)
        self.assertEqual(target, a)
        self.complete(target)
        self.assertEqual(a.read_text().splitlines().count('Initial prompt'), 2)
        self.assertEqual(source.read_text(), original)

    def test_prompt_already_typed_in_the_target_buffer_is_not_copied_again(self):
        a = self.prepare('Initial prompt')
        self.complete(a)
        self.client.edit(a.resolve().as_uri(), '\nLocal follow-up\n')
        self.prepare('Local follow-up', a.read_text().splitlines()[0], mode='resume', source=a)
        self.complete(a)
        self.assertEqual(a.read_text().splitlines().count('Local follow-up'), 1)

    def test_buffer_context_is_literal_even_with_quotes_shell_text_and_newlines(self):
        source = self.directory / "copy 'quoted' $(touch INJECTED)\ntouch ALSO_INJECTED"
        source.write_text('Source buffer')
        script = shlex.join([sys.executable, str(BUFFER), 'capture', 'codex', 'new', '--line-start', '1'])
        script += ' --buffer-context "$BASH_EXECUTION_STRING"; exit # helix-agent-buffer: ' + str(source)
        result = subprocess.run(['bash', '-c', script], input='Literal prompt', text=True,
                                env=self.env, cwd=self.directory, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        pending = json.loads((self.state / 'pending/test-editor.json').read_text())
        self.assertEqual(pending['source_uri'], source.resolve().as_uri())
        self.assertEqual(pending['prompt'], 'Literal prompt')
        self.assertFalse((self.directory / 'INJECTED').exists())
        self.assertFalse((self.directory / 'ALSO_INJECTED').exists())

    def test_agent_uses_the_requesting_editors_working_directory(self):
        a = self.prepare('Check the working directory')
        self.complete(a)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(calls[-1]['cwd'], str(Path.cwd()))

    def test_progress_tokens_end_on_success_and_failure(self):
        a = self.prepare('Initial prompt')
        self.complete(a)
        self.client.pump_until(lambda: any(update['kind'] == 'end' for _, update in self.client.progress_events))
        self.assertFalse(self.client.progress_active)
        self.settings.write_text(json.dumps({'AGENT_TEST_BEHAVIOR': 'network'}))
        self.prepare('Follow-up', a.read_text().splitlines()[0], mode='resume')
        self.command('start')
        self.client.pump_until(lambda: sum(update['kind'] == 'end' for _, update in self.client.progress_events) == 2)
        ends = [update for _, update in self.client.progress_events if update['kind'] == 'end']
        self.assertEqual([update['message'] for update in ends], ['Finished', 'Failed'])
        self.assertFalse(self.client.progress_active)
        self.assertEqual(len(self.client.progress_created), 2)

    def test_nearby_chunks_are_batched_into_fewer_workspace_edits(self):
        a = self.prepare('Stream many small chunks')
        self.settings.write_text(json.dumps({'AGENT_TEST_BEHAVIOR': 'burst'}))
        self.command('start')
        uri = a.resolve().as_uri()
        self.client.pump_until(lambda: 'BURST_29' in self.client.documents[uri]['text'])
        self.assertEqual(self.client.documents[uri]['text'].count('BURST_'), 30)
        self.assertLessEqual(len(self.client.applied_edits), 5)

    def test_bare_cursor_does_not_launch_an_agent(self):
        for cursor in ('a', 'e\u0301', '👨\u200d👩\u200d👧', '🇨🇦'):
            with self.subTest(cursor=cursor):
                self.prepare(cursor)
                self.command('start')
                self.assertFalse(self.log.exists())


if __name__ == '__main__':
    unittest.main()

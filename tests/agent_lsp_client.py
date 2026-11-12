"""A small LSP client for exercising the bridge without calling a model."""

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


class Client:
    def __init__(self, env, cwd=None):
        self.documents = {}
        self.messages = queue.Queue()
        self.responses = {}
        self.force_race = False
        self.rejected_edits = 0
        self.applied_edits = []
        self.progress_created = set()
        self.progress_active = {}
        self.progress_events = []
        self.errors = tempfile.TemporaryFile()
        self.process = subprocess.Popen(
            [sys.executable, str(ROOT / 'bin/agent-buffer-lsp')],
            env=env, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors,
        )
        threading.Thread(target=self.read, daemon=True).start()
        self.send({'id': 0, 'method': 'initialize', 'params': {'capabilities': {'window': {'workDoneProgress': True}}}})
        self.pump_until(lambda: 0 in self.responses)
        self.send({'method': 'initialized', 'params': {}})

    def send(self, value):
        data = json.dumps({'jsonrpc': '2.0', **value}).encode()
        self.process.stdin.write(b'Content-Length: ' + str(len(data)).encode() + b'\r\n\r\n' + data)
        self.process.stdin.flush()

    def read(self):
        while True:
            headers = {}
            while True:
                line = self.process.stdout.readline()
                if not line:
                    self.messages.put(None)
                    return
                if line == b'\r\n':
                    break
                key, value = line.decode().split(':', 1)
                headers[key.lower()] = value.strip()
            data = self.process.stdout.read(int(headers['content-length']))
            self.messages.put(json.loads(data))

    def open(self, path):
        uri = path.resolve().as_uri()
        if uri not in self.documents:
            self.documents[uri] = {'uri': uri, 'version': 0, 'languageId': 'markdown', 'text': path.read_text()}
            self.send({'method': 'textDocument/didOpen', 'params': {'textDocument': self.documents[uri]}})
        return uri

    def edit(self, uri, text):
        doc = self.documents[uri]
        doc['text'] += text
        doc['version'] += 1
        self.send({'method': 'textDocument/didChange', 'params': {
            'textDocument': {'uri': uri, 'version': doc['version']},
            'contentChanges': [{'text': doc['text']}],
        }})

    def handle(self, value):
        if value is None:
            self.errors.seek(0)
            raise RuntimeError('Bridge exited: ' + self.errors.read().decode(errors='replace'))
        if value.get('method') == 'window/workDoneProgress/create':
            token = value['params']['token']
            self.progress_created.add(token)
            self.send({'id': value['id'], 'result': None})
        elif value.get('method') == '$/progress':
            token, update = value['params']['token'], value['params']['value']
            assert token in self.progress_created
            self.progress_events.append((token, update))
            if update['kind'] == 'begin':
                self.progress_active[token] = update
            elif update['kind'] == 'end':
                self.progress_active.pop(token, None)
        elif value.get('method') == 'workspace/applyEdit':
            changes = value['params']['edit']['documentChanges']
            assert len(changes) == 1
            change = changes[0]
            uri = change['textDocument']['uri']
            if self.force_race:
                self.force_race = False
                self.edit(uri, 'UNSAVED_RACING_EDIT界😀')
            doc = self.documents[uri]
            applied = doc['version'] == change['textDocument']['version']
            if applied:
                lines = doc['text'].split('\n')
                eof = {'line': len(lines)-1, 'character': len(lines[-1].encode('utf-16-le'))//2}
                for edit in change['edits']:
                    assert edit['range'] == {'start': eof, 'end': eof}, edit
                    self.applied_edits.append((uri, edit['newText']))
                    self.edit(uri, edit['newText'])
            else:
                self.rejected_edits += 1
            self.send({'id': value['id'], 'result': {'applied': applied}})
        elif 'id' in value and 'method' not in value:
            self.responses[value['id']] = value.get('result')
        elif 'id' in value:
            self.send({'id': value['id'], 'result': None})

    def pump_until(self, predicate, timeout=15):
        end = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > end:
                raise TimeoutError('Timed out waiting for bridge output')
            try:
                self.handle(self.messages.get(timeout=.05))
            except queue.Empty:
                pass

    def close(self):
        if self.process.poll() is None:
            self.send({'method': 'exit', 'params': {}})
            self.process.stdin.close()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process.stdout.close()
        self.errors.close()

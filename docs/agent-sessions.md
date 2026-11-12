# Buffer-specific agent conversations (tentative)

This integration uses configuration and local Python helpers. It uses Helix's
existing language-server edit interface; it does not patch or rebuild Helix.
There are no read-only toggles, file-reload loops or blocking model calls in the
bindings. Replies append to the live buffer while it remains editable.

Reload bindings with `:config-reload`. After updating the helper while an
`agent-chat` buffer is already open, let active replies finish and run
`:lsp-restart` in that buffer once. Select your prompt and use these shortcuts:

| Agent | Start a conversation | Resume a conversation |
| --- | --- | --- |
| Codex | `space . V` | `space . v` |
| Claude | `space . C` | `space . c` |
| Grok | `space . G` | `space . g` |
| agy | `space . A` | `space . a` |

Starting a conversation opens a Markdown buffer whose first line is a reference:

```markdown
# helix-agent-session: 7cda2a7e10bd4f78805f286e44950e86
```

New conversation filenames use a slug of the first nonempty prompt line and a
short hash, for example `fix-login-bug-7cda2a.md`. This gives `space b` readable
conversation names. Follow-up prompts keep the original filename; existing
hash-only files remain supported. The full first-line reference determines the
conversation, including when short filename suffixes collide.

`agent-chat` inherits Markdown code-block folding and adds heading-section
folds, alongside its inherited highlighting and injections. Run `:config-reload`
to load query changes.

The full first-line reference maps to each agent's actual ID in a local registry.
Resume reads it independently of the selection and returns to the buffer where
that conversation started. Starting another conversation, or running `::` in
another buffer, does not change that association. A copied reference returns to
the same original conversation file.
When you send from a different buffer containing a copied reference, the selected
prompt is copied into the original conversation before the reply. Prompts already
selected in the original conversation are not duplicated. The agent runs in the
requesting editor's working directory.

Type your follow-up in the conversation buffer, select it, and press the
lowercase shortcut. Each output chunk inserts at the buffer's current end.
Unsaved edits remain in place. If you type while an append edit is in flight,
the helper retries that chunk against the newer document version and EOF.
Output can interleave with a draft you are typing at the end.

Nearby output chunks are coalesced into batches at roughly 200 ms intervals,
with a final flush on completion or cancellation. This reduces undo steps while
keeping streaming responsive. **Each applied batch is still a separate undo
step.** Helix's LSP interface does not expose whole-reply undo grouping, and
normal undo history can interleave your edits with agent output.

The statusline spinner uses standard LSP work-done progress. It stays active
while the agent is thinking or running tools, including periods with no output,
and ends on completion, failure or cancellation.

**`space . q` cancels this conversation's running and queued requests.** It also
stops agent child processes. The editor remains responsive during replies.
Ordinary `::` commands keep their existing behavior; `:::` / `:cancel-stream`
continues to control those native streams. Agent requests use `space . q`.

The primary selection is passed literally, including quotes, shell syntax and
newlines. One trailing line ending is removed. If the selection overlaps the
first-line marker, that metadata is omitted from the prompt. Source buffers
used to start a conversation are preserved, including unsaved text.

If a marker, registry entry or native conversation is missing, resume uses the
agent's existing most-recent behavior and prints a notice. The actual ID
reported by that run is recorded. Connection and authentication failures do not
retry the prompt in another conversation. IDs come from native structured
output, rather than a search for the latest session file. For Codex, see
[the official non-interactive mode guide](https://learn.chatgpt.com/docs/non-interactive-mode).
The agent permission flags match the previous shortcuts.

Conversation files and the ID registry live under
`~/.local/state/helix/agent-sessions/`, or the corresponding `XDG_STATE_HOME`.
`HELIX_AGENT_STATE_DIR` overrides that location. The reference requires the
local registry; deleting it restores the most-recent fallback behavior.

Native IDs are saved automatically. **Save the transcript with `:w`**, as with
other edited buffers. Streaming does not rewrite its file behind your edits.
Closing the conversation buffer or editor stops its running agent request.

The `agent-chat` language starts `bin/agent-buffer-lsp` inside Helix's normal
language-server lifecycle. That helper applies versioned append edits to the
original document URI. It consumes requests from `bin/agent-buffer` and starts
`bin/agent-session` to translate each CLI's structured output. Requests for one
conversation run in order; separate conversation buffers can run independently.
No model is invoked merely by opening a file or starting the language server.

Tests use fake agents and the installed editor, without live model calls:

```sh
python3 -m unittest discover -s tests -p 'test_agent*.py' -v
```

They cover explicit IDs and fallback, literal prompt text, interleaving
conversations and ordinary `::` commands, partial output before completion,
editing during output, stale-edit retries, cross-buffer prompt copies, batched
undo steps, spinner lifecycle, and cancelling an agent and its child.
The editor tests disable auto-reload to verify that output reaches the live
buffer directly. Native event formats are tested with representative events.

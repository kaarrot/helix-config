# Helix todo workflow findings

I reproduced these issues with Helix 25.07.1 (`803d7f22`) using disposable
task files and caches. After the fixes, all 312 `td` tests and 61 `tl` tests
passed. I replayed the shortcuts in Helix and used a fixed clock and the
dry-run scheduler for the reminder checks.

## Agenda actions could target the wrong todo (fixed)

Put these two lines in `todo.md` and open the agenda with `Space , a`.

```markdown
- [ ] Send update → https://example.test/alpha
- [ ] Send update → https://example.test/beta
```

On the second row, `Space , p` jumped to the first line, and `Space , x` marked the first line done. In a separate run, `Space , N` showed the second row's text in the prompt and applied the rename to the first line. The lookup strips the visible `→ link` from both rows and uses the first match with the same text and status.

`p`, `x`, and `N` now match the full task text, including the link. I verified that each action on the second row affects the second bullet. [Inbox lookup](../bin/td#L3293)

## A failed source save could leave notes in both files (fixed)

I edited a todo in Helix, added a separate line to `todo.md` on disk, and tried `Space , Enter` and `Space , P` in separate runs. The first appended the section to `day.md`. The second copied the notes to the dedicated task file. Helix rejected the inbox save in both runs because the file had changed on disk, leaving the original notes in the saved inbox too. Both commands write the destination before the shortcut saves the source. After a successful move, undoing it in the inbox and saving also leaves a copy in each file.

`P` and `Enter` now wait for the source to be saved before moving notes. I verified both keys with conflicting edits on disk and with a successful move followed by undo, save, redo, and save. If the destination has changed on disk, Helix reports the conflict and keeps the edited destination. [Move handler](../bin/td#L2865) · [Undoing a move](keys.md#undoing-a-move)

## Promotion return position (fixed)

Before the fix, promoting a todo at `todo.md:3:9` and returning with either `ga` or `Ctrl+o` landed at `todo.md:7:10`. The whole-buffer pipe had moved the cursor to the end before Helix switched files.

The updated binding restores the source cursor before leaving for the promoted file. Both keys now return to `todo.md:3:9` in the same test. A second `Ctrl+o` returns to the earlier buffer. I verified both return keys with saved and unsaved source edits. [Promotion binding](../config.toml#L151)

## Clocking in from the agenda could leave no timer running (fixed)

With a timer running in a task file, I pressed `Space , i` on a different task's agenda row. The old timer closed at the current time. Helix then tried to save the new time entry in the read-only agenda and refused the write. `tl where --say` reported `nothing running`.

`i` and `I` resolve the task's source before switching timers. I verified that both keys start on the selected task and that an agenda heading leaves the existing timer running. [Clock-in target](../bin/tl#L432)

## A time-log heading could close its parent task (fixed)

In a linked file, I pressed `Space , x` on `# Sketched pages`, the heading above a time entry. The shortcut changed it to `# [x] Sketched pages` and marked the task's inbox bullet done. The file's actual title still showed `# [ ] Deck notes`. The status command treats any level-one heading in the task file as its title. The scheduler uses the now-closed inbox bullet to determine whether the file's reminders are eligible.

The status keys use the first-line heading for the task title. I verified that the later time-log heading leaves both files as they were, and that pressing the key on the title still completes the task. [Status command](../bin/td#L3004)

## Moving a completed task could schedule a reminder from its notes (fixed)

In the inbox, a note saying `Reference time [2026-11-23 Mon 10:05]` under a completed task produced no reminder. After I moved that task to an open `day.md` with `Space , Enter`, the dry-run scheduler armed 10:05 and reported that it would fire `Reference time [day]` at that time. The move puts the note inside a Markdown code fence, and the scheduler scans timestamps inside that fence.

The scheduler skips Markdown code fences. I repeated the move and confirmed that the reference time stayed in the archive and produced no reminder. [Fence handling](../bin/td#L637)

## Source edits could leave the agenda stale (fixed)

`Space , x` in the inbox saved the task as `[x]` while the cached open agenda still showed `[ ]`. The status command rebuilds the agenda before Helix saves the inbox. `Space , Enter` likewise left a moved task in the cached Done agenda because that move leaves the agenda snapshot in place. Reopening the relevant agenda view rebuilds it from the saved files.

A saved task edit refreshes the latest agenda with its current sort and filters. A move also refreshes the agenda once it finishes. I verified the cached view after a status change and after moving a task from the Done view. [After-save handler](../bin/td#L1808)

## Capture keys ignored a configured inbox (fixed)

With `TD_FILE` pointing to `~/tasks/inbox.md`, `Space , q` and `Space , Q` still wrote new todos to `~/tasks/todo.md`. The agenda read `inbox.md` and omitted both new todos. The `t` and `Space` bindings also use the literal default path.

The capture keys and `t` use the same inbox setting as the agenda. I verified all four bindings with an inbox path containing spaces. [Inbox bindings](../config.toml#L123)

## Spaces in a task filename broke the in-file status key (fixed)

In `~/tasks/Travel plans.md`, `Space , x` left the task heading open. The same key on its agenda row completed the task. The in-file binding passes the filename to the shell without quoting, so the status command receives only the first word as its source path.

The status bindings pass the full buffer path to `td`. I verified the key on a task file with spaces, quotes, and a dollar sign in its name. [Status binding](../config.toml#L175)

## Reopening an uppercase `[X]` task took two presses (fixed)

In the Done agenda, the first `Space , x` changed `[X]` to `[x]`. The second reopened it. The Done view includes both spellings, and the toggle compares them as separate states.

Both spellings now reopen with one press. I verified an inbox bullet and a standalone file from the Done agenda. [State comparison](../bin/td#L281)

## A saved reminder needed a separate scheduler action (fixed)

The documented sequence is `Space , s`, adjust the time, save, then open the agenda. The last step starts the scheduler. A reminder saved with `:w` waits for the next tick, so a new deadline can pass before it gets armed.

The `td-save` language server runs the scheduler after a successful Helix save. I verified that a plain `:w` arms a new reminder without opening the agenda. [Save hook](../languages.toml#L88) · [Reminder setup](../README.md#L55)

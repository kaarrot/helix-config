# `td` / `tl` keys

Every key under `space ,` (`[keys.normal.space.","]` in `../config.toml`)
and the `+`/`-` stamp keys in `[keys.normal]`. The config gives each key a
one-line comment; this file is the full description. `td test` checks that
this file and the config list the same keys, so add or remove a row here
whenever you add or remove a key there.

The design behind them (task files, reminders, the agenda) is in
[agenda.md](agenda.md).

All keys below except `+`/`-` are pressed after `space ,`.

## Time log (`tl`)

Task files are the `*.md` and `*.txt` files in `~/tasks` (`$TL_DIR`). A
time-log entry is a line that starts with date, time and a dash, optionally
after `- `, `* ` or `- [ ] `:

```
2026-10-13 09:30 - 10:45 = 1h 15min  note
2026-10-13 13:00 -                     (running: no end time yet)
```

The `= 1h 15min` part is only for reading; totals are always worked out
from the times. todo.md is not a task file for `tl`: its bullets are todos.

| Key | What it does |
|---|---|
| `i` | **Clock in.** First ends every entry still running that started less than 12 hours ago, in the other task files on disk and in this buffer (without saving it). Then adds `YYYY-MM-DD HH:MM - ` on a new line at the end of the buffer and leaves you in insert mode to type the note. In todo.md the new line is not an entry: `tl` skips todo.md, so it is never stopped or counted |
| `o` | **Clock out.** Saves all buffers, then waits at the command prompt `# done: `. Type what you did and press Enter: the latest running entry (in any task file, started in the last 12 hours) gets its end time and duration, and your text becomes the `# heading` line right above it, or is added to the heading already there after ` - `. Enter on an empty prompt ends the entry with no heading; Esc does nothing. The text needs no quoting; only `%` is special (type `%%` for one) |
| `r` | **Recent files.** A popup with the 9 most recently changed task files, newest first, each with its last entry. Open one with `:o <path>` |
| `S` | **Summary.** Saves, then shows time per day for the last 14 days in a popup: per task file its total and title, and under it the `# headings` it was worked under. Running entries come first, and problems (overlaps, duplicates, typos, entries over 12 hours) last, as `~/path:line` you can open with `gf`. In a file outside `~/tasks`, only that file is counted |

## Todos (`td`)

todo.md (`~/tasks/todo.md`, or `$TD_FILE`) is the inbox and the source of
truth: one bullet per task, with the state in the checkbox.

| State | Checkbox |
|---|---|
| todo | `[ ]` |
| today | `[Y]` |
| active | `[A]` |
| waiting | `[W]` |
| done | `[x]` |
| ignore | `[!]` |

A task can have its own notes file, `~/tasks/<slug>.md`, named after the
bullet's text (`Call the bank!` → `call-the-bank.md`; a trailing stamp is
left out). Renaming the bullet unlinks it from its file.

| Key | What it does |
|---|---|
| `t` | Open the inbox, `~/tasks/todo.md` |
| `a` | **Agenda.** Opens a snapshot of todo.md grouped TODAY, ACTIVE, TODO, WAITING, newest-added first; done and ignored bullets are hidden. A bullet with its own file shows ` (*)`. Files without a bullet are listed by the status on their first line (`# [W] renew passport`), or under ORPHANS if they have none. View only: Helix shows `[readonly]`, and anything typed there is thrown away by the next `a`. Change tasks in todo.md; `p` takes you there |
| `A` | The same agenda, most recently changed first: a bullet's line (state, text, stamp) or its own file. Edits by hand count from the next `a`, `A` or status key |
| `p` | **Go to the task.** On a bullet: open its own file, if it has one; otherwise stay. On an agenda row: go to that bullet's line in todo.md; a row for a file goes to the file. Never creates anything. Uses the line as it is in the buffer, saved or not |
| `P` | **Give the task a file.** Saves, then creates `~/tasks/<slug>.md` for the bullet, with a heading `# [S] title` that carries the bullet's state, and opens it. An existing file is reused and its heading's state updated. On an agenda row it only opens the row's file, if any. Works on a bullet you have just typed, saved or not |
| `x` | **Done.** Toggles `[ ]` ↔ `[x]`. If the line has a repeater after its stamp, `++Nu` or `.+Nu` (N a number, u = `d`/`w`/`m`/`y`), the date moves instead and the bullet stays `[ ]`: `++1m` moves it a month at a time until it is in the future (rent on the 1st), `.+2w` sets it to today + 2 weeks (water the plants). See [Status keys in other files](#status-keys-in-other-files) |
| `s` | **Stamp.** On a line with no date, adds today's date and the current time at the end: `2026-10-13 Tue 09:30`. On a line with one, changes its date to today and keeps the time. With the cursor on the date (after editing it by hand), keeps the date and only fixes the weekday. A time-log entry's leading time is history, so a fresh stamp is added at the end. A stamp of "now" never fires a reminder; edit it to a later time and it will |
| `Enter` | **Check reminders now.** Saves, then runs the same check as the 15-minute job (`td-tick`) |
| `, y` | Toggle `[ ]` ↔ `[Y]` (today) |
| `, a` | Toggle `[ ]` ↔ `[A]` (active) |
| `, w` | Toggle `[ ]` ↔ `[W]` (waiting) |
| `, x` | Toggle `[ ]` ↔ `[x]` (done), the same as `x` |
| `, space` | Set `[ ]` (todo); on a heading, `# [ ]` |

Each `, ` status key is the letter its checkbox gets: `, y` writes `[Y]`,
`, x` writes `[x]`, and `, space` the empty `[ ]`.

### Status keys in other files

`x` and the `, ` keys work on any bullet, change the line at once, and then
save the file. They also keep the task's other copies in step:

- **In todo.md:** the bullet changes, and so does the state on its own
  file's heading.
- **On a task file's heading** `# [S] title`: the heading toggles, and the
  todo.md bullet the file belongs to gets the same state. The file name
  finds the bullet, so a heading you retitled still works. Marking a
  repeating bullet done moves its date, and the heading goes back to `[ ]`.
- **On a bullet in another file with the same text as a todo.md bullet:**
  that todo.md bullet changes too.
- **On any other bullet** (subtasks): only that line.
- **On the agenda:** nothing; it is a view.

If several todo.md bullets have the same text (an old done `call mom` and a
new one), the open one changes. A state typed by hand doesn't reach other
copies; only these keys do. Reminders don't depend on that: a task file
fires while its todo.md bullet is open, whatever its heading says.

`space . x` (not a `td` key) toggles `[ ]` ↔ `[X]` with `sed` in any file:
no repeaters, and no other copies change.

## Moving a stamp (normal mode, no `space ,`)

`+` moves the stamp (`YYYY-MM-DD Xxx HH:MM`) on the cursor's line later and
`-` moves it earlier, by the part under the cursor. The cursor stays on that
part, so pressing again keeps moving it. The weekday follows the date, and
one undo reverts one press. A line with no stamp is left alone, and so is
the agenda. These keys don't save.

| Key | What it does |
|---|---|
| `+` | Later by one year, month, day, hour, or 5 minutes, whichever the cursor is on. On the weekday or anywhere else on the line: one day |
| `-` | The same, earlier |

Minutes land on multiples of 5 (`09:32` → `09:35` / `09:30`). Hours past
midnight change the day; a month from the 31st lands on the month's last day.

## How the keys are built

Helix runs a key's commands in order, but not all of them finish before
the next one starts:

- `:write` and `:update` save in the background: the file on disk changes
  only after the whole key has run.
- `:sh` runs in the background too, alongside whatever comes next.
- `%sh{…}` inside a command, `:pipe` and `:pipe-to` finish before the next
  command runs.

So the keys that work on the current line use only the last kind, and
`td` gets the line from the buffer, never from the file on disk. `S` and
`Enter` save and then run `:sh`, both in the background; the save is quick
next to starting Python, so they see the saved file in practice.

- **Status keys, `x`, `s`, `+`, `-`:** `extend_to_line_bounds` selects the
  line, and `:pipe` sends it through `td` and puts the result in its place,
  so the change shows at once and unsaved edits are kept. The status keys
  and `x` then `:write`. `td` writes other files (todo.md, a task file's
  heading) itself. `:pipe` puts anything printed on stderr in place of the
  line, so `td` prints nothing there. Two earlier designs failed: `:write`
  then `:sh td … --line N` showed the change only on the next keypress, so
  pressing again toggled it back; `:write` then `%sh{td … --line N}` and
  `:reload` raced the save, so Helix refused to save over `td`'s change and
  `:reload` dropped unsaved edits.
- **`p`, `P`:** `:pipe-to` sends the line to `td` without changing the
  buffer. `td` writes where to go to `~/.cache/td/open`, and
  `:open %sh{cat …}` goes there, then deletes the file so a failed run
  can't send you somewhere old. (`P` used to create the file with `:sh` and
  open it with `%sh{}`, so whether it opened depended on which finished
  first.) `P` saves with `:update`, not `:write`: todo.md is saved before you
  leave it (`td` writes it when you change the state in the new file), and
  the read-only agenda is never written.
- **`s`, `+`, `-`** need the cursor column, but `extend_to_line_bounds`
  moves the cursor to the line end. So the first command saves
  `%{cursor_column}` to `~/.cache/td/stamp-col`, and `td` reads it. `+`/`-`
  get back the column where the moved part now is, and
  `:open FILE:LINE:COL` puts the cursor there.
- **`a`, `A`:** `td list` runs inside `%sh{}`, so the agenda is rebuilt
  before `:open`, and `:reload` drops anything typed into the read-only
  buffer.
- **`i`:** `tl stop` runs inside `%sh{}` for the other files, then the
  whole buffer goes through `:pipe tl stop -` (a `:write` would land too
  late), then `tl start`'s output goes on a new last line.
- **`o`** is a macro, so the command prompt stays open for you to type.
  The prompt holds `:sh tl out "$BASH_EXECUTION_STRING" # done: `, so what
  you type is a shell comment, which bash ignores. `tl` reads it back from
  `$BASH_EXECUTION_STRING` (the whole command line), so it needs no
  quoting. `tl` looks for exactly `"$BASH_EXECUTION_STRING" # done:`
  (`DONE_MARK` in `tl`): change both together.
- **`S`** runs `align_view_top` first: a popup opens below the cursor's
  screen row when 6 rows fit there, so at the top it gets the full height.

### Why `p` and `P` are separate

Bullets carry no link to their file: it is found from the bullet's text. If
one key both jumped and created, a typo would make a stray file
(`refacror td parser` → `refacror-td-parser.md`). So `p` only goes where
something exists, and `P` (capital: more deliberate) is the one that
creates.

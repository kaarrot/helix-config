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
| `i` | **Clock in.** First ends what is running (every entry that started less than 12 hours ago and has no end), in whichever task file it is, keeping a note you typed there and haven't saved; that file is saved. Then adds `YYYY-MM-DD HH:MM - ` on a new line at the end of this buffer, saves it so the next clock-in can find the entry, and leaves you in insert mode to type the note. In todo.md the new line is not an entry: `tl` skips todo.md, so it is never stopped or counted |
| `I` | **Switch back.** Ends what is running, as `i` does (no heading), and clocks in to the task you worked on before it: opens that task file and adds `YYYY-MM-DD HH:MM - ` at its end, in insert mode. "Before it" means the latest entry in a file other than the running entry's, so pressing `I` again switches back. With nothing running (say after `o`), it resumes the task of the latest entry. If there is no other task, it works like `i` in this buffer. Both files are saved, as with `i` |
| `L` | **Week summary in a buffer**, to copy from. Saves, then opens `~/.cache/tl/summary.txt` with the same report as `l`, for this week, Monday to Sunday, over all task files (wherever you press it). The file is rewritten each time and read-only, like the agenda; anything typed there is thrown away by the next `L`. In it, `-` and `+` show the previous and next week, as often as you press them; `L` goes back to this week |
| `o` | **Clock out.** Saves all buffers, then waits at the command prompt `# done: `. Type what you did and press Enter: the latest running entry (in any task file, started in the last 12 hours) gets its end time and duration, and your text becomes the `# heading` line right above it, or is added to the heading already there after ` - `. Enter on an empty prompt ends the entry with no heading; Esc does nothing. The text needs no quoting; only `%` is special (type `%%` for one) |
| `O` | **Clock out and switch back.** `o` and `I` in one. Saves all buffers, ends the running entry and anything else still running, and clocks in to the task you worked on before it, as `I` does: `YYYY-MM-DD HH:MM - ` at the end of that task's file. Then it waits at the `# done: ` prompt: type what you did and press Enter, and your text becomes the ended entry's heading, as with `o`, and the task you switched to opens on its new entry, in normal mode (`A` to type a note). Enter on an empty prompt adds no heading; Esc leaves you where you are, with the clock already switched. With nothing running, it resumes the task of the latest entry; with no other task, it only clocks out. As with `n`, `%` is typed `%%`, and the text can't contain `}` |
| `r` | **Recent files.** A popup with the 9 most recently changed task files, newest first, each with its last entry. Open one with `:o <path>` |
| `l` | **Summary** (time log). Saves, then shows time per day for the last 14 days in a popup: per task file its total and title, and under it the `# headings` it was worked under. Running entries come first, and problems (overlaps, duplicates, typos, entries over 12 hours) last, as `~/path:line` you can open with `gf`. Always over all task files, wherever you press it (the agenda too) |

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
| `q` | **New todo.** Opens todo.md and adds `- [ ] ` on a new first line, in insert mode: type the task, then save. If the first line already is an empty `- [ ] ` (say a `q` you left without typing), it goes there instead of adding a second one; anything else moves down a line. Works from anywhere, the agenda too; the agenda shows the task after the next `a` |
| `Q` | **New todo at the end.** The same as `q`, on a new last line of todo.md: an empty `- [ ] ` already last is used |
| `space` | The same as `q` |
| `n` | **New file task**, for a task clear enough to skip todo.md. Opens the command prompt at `# name: `; type the task's name and press Enter (Esc does nothing). Creates `~/tasks/<slug>.md`, named like a bullet's own file (`Buy a car!` → `buy-a-car.md`), with `# [ ] Buy a car!` on its first line, and opens it on the blank line under the heading. It is a file task: the agenda lists it under TODO, and the status keys on its heading set its state. If the file exists, it just opens it. The name needs no quoting; only `%` is special (`%%` for one), and it can't contain `}` |
| `N` | **Rename a task**, from its agenda row. Opens the command prompt at `# name: ` with the task's current name filled in; edit it, or delete it and type a new one, then press Enter (Esc does nothing). The new name goes through the same check as `n`'s, and the task changes where it lives: a file task's (or orphan's) file is renamed to the new name's slug and its first-line heading gets the name, keeping its `[S]`; a bullet row's todo.md bullet gets the name as its text, and its own file, if any, is renamed and retitled with it, so the two stay linked. The agenda reloads, and the task keeps its place in it. Refused, changing nothing, when a file already has the new name, the name has no letter or digit, or the row shows no task. As with `n`, `%` is typed `%%`, and the name can't contain `}`. Don't rename a file you have open in another buffer: that buffer keeps the old name |
| `a` | **Agenda.** Opens a snapshot of todo.md grouped TODAY, ACTIVE, TODO, WAITING, newest-added first; done and ignored bullets are hidden. After TODAY, under RESCHEDULE, the reminders that went off while their task is still open (not those on a line with a `++`/`.+` repeater), each pointing at its date: `p` there to move it with `+`/`-`. A bullet with its own file shows ` (*)`. Files without a bullet are listed by the status on their first line (`# [W] renew passport`), or under ORPHANS if they have none. View only: Helix shows `[readonly]`, and anything typed there is thrown away by the next `a`. But `x` and the status keys work on its rows: they change the task itself (see below), and the agenda reloads. `q` adds a new task, `n` a new file task, and `N` renames the task on a row. For anything else, `p` takes you to the task |
| `A` | The same agenda, most recently changed first: a bullet's line (state, text, stamp) or its own file. Edits by hand count from the next `a`, `A` or status key |
| `D` | **Done tasks.** The agenda with only the done ones under DONE: `[x]` bullets and files whose first line is `# [x] title`, most recently changed first, as `A` orders them. `x` on a row takes the task back to `[ ]` and the row drops out; `p` goes to the task. `a` brings back the open ones |
| `p` | **Go to the task.** On a bullet: open its own file, if it has one; otherwise stay. On an agenda row: go to that bullet's line in todo.md; a row for a file goes to the file; a RESCHEDULE row goes to the reminder's line, the cursor on its day. Never creates anything. Uses the line as it is in the buffer, saved or not |
| `P` | **Give the task a file.** Saves, then creates `~/tasks/<slug>.md` for the bullet, with a heading `# [S] title` that carries the bullet's state (the title leaves out the bullet's stamp and repeater: the reminder stays on the bullet), and opens it. An existing file is reused and its heading's state updated. On an agenda row it only opens the row's file, if any. Works on a bullet you have just typed, saved or not |
| `x` | **Done.** Toggles `[ ]` ↔ `[x]`. If the line has a repeater after its stamp, `++Nu` or `.+Nu` (N a number, u = `d`/`w`/`m`/`y`), the date moves instead and the bullet stays `[ ]`: `++1m` moves it a month at a time until it is in the future (rent on the 1st), `.+2w` sets it to today + 2 weeks (water the plants). An hourly one (`++1h`, a reminder every hour until done) is just marked done. A task file with no todo.md bullet repeats the same way, with the date and repeater on any line but a bullet (`2026-12-15 Tue 11:50 ++2m` under `# [ ] haircut`). See [Status keys in other files](#status-keys-in-other-files) |
| `s` | **Stamp.** On a line with no date, adds today's date and the current time at the end, in brackets: `[2026-10-13 Tue 09:30]`, which keeps it grey and out of an open task's bold. On a line with one, changes its date to today and keeps the time. With the cursor on the date (after editing it by hand), keeps the date and only fixes the weekday. A time-log entry's leading time is history, so a fresh stamp is added at the end. A stamp of "now" never fires a reminder; edit it to a later time and it will. With two stamps on the line, the cursor picks which one changes. Doesn't save: the reminder alarm learns the new time once the file is saved, at the next tick (opening the agenda runs one) |
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

- **On an agenda row:** the row itself stays as it is; the task it shows
  changes where it lives: the todo.md bullet (found by its state and text,
  as `p` finds it, and its own file's heading follows), or, on a file-task
  row, that file's `# [S] title` heading. Then the agenda is rebuilt, in
  the order you opened it (`a` or `A`), and Helix reloads it. A row that
  is out of date (its bullet changed since) only gets the rebuild.

- **In todo.md:** the bullet changes, and so does the state on its own
  file's heading.
- **On a task file's heading** `# [S] title`: the heading toggles, and the
  todo.md bullet the file belongs to gets the same state. The file name
  finds the bullet, so a heading you retitled still works. Marking a
  repeating bullet done moves its date, and the heading goes back to `[ ]`.
- **On a file task** (a task file with no todo.md bullet) with a repeating
  date on a line that isn't a bullet: `x` on its agenda row, or on the
  date's line, moves the date, and the heading stays `[ ]`. On the heading
  itself, `x` moves a date on that same line; with the date on another
  line it changes nothing, since the key gets only the heading's line and
  can't reach the date (and marking it done would end the repeats).
- **On a bullet in another file in ~/tasks with the same text as a todo.md
  bullet:** that todo.md bullet changes too.
- **On any other bullet** (subtasks): only that line.
- **Outside ~/tasks** (a README's checklist): only that line, whatever its
  text; todo.md and the task files are left alone.

If several todo.md bullets have the same text (an old done `call mom` and a
new one), the open one changes. A state typed by hand doesn't reach other
copies; only these keys do. Reminders don't depend on that: a task file
fires while its todo.md bullet is open, whatever its heading says.

`space . x` (not a `td` key) toggles `[ ]` ↔ `[X]` with `sed` in any file:
no repeaters, and no other copies change.

## Moving a stamp or a time-log entry (normal mode, no `space ,`)

`+` moves the stamp (`YYYY-MM-DD Xxx HH:MM`) on the cursor's line later and
`-` moves it earlier, by the part under the cursor (on a line with two
stamps, the one the cursor is on, else the first). The cursor stays on that
part, so pressing again keeps moving it. The weekday follows the date, and
one undo reverts one press. A line with no stamp is left alone, and so is
the agenda. These keys don't save, so the reminder alarm learns the new
time as it does a hand edit: once saved, at the next tick (opening the
agenda runs one).

On the week summary view (`space , L`), `-` shows the previous week and `+`
the next one, wherever the cursor is.

On a time-log line (`2026-10-13 09:30 - 10:45 = 1h 15min  note`) they amend
the entry instead: its date, its start time or its end time, whichever the
cursor is on, and the `= 1h 15min` part is worked out again. On the note,
the entry's date moves, unless the line also has a reminder stamp, whose
day moves then. The line keeps `tl`'s shape (no weekday is added), so it
stays a time-log entry and never becomes a reminder, wherever its date
goes. A start moved past midnight takes the date with it; the end is just
a time of day.

| Key | What it does |
|---|---|
| `+` | Later by one year, month, day, hour, or 5 minutes, whichever the cursor is on. On the weekday or anywhere else on the line: one day. On a time-log line: the same for its date, start or end time |
| `-` | The same, earlier. On the week summary view: the previous week (`+`: the next) |

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
`td` gets the line from the buffer, never from the file on disk. `l` saves
and then runs `:sh`, both in the background; the save is quick next to
starting Python, so it sees the saved file in practice.

- **Status keys, `x`, `s`, `+`, `-`:** `extend_to_line_bounds` selects the
  line, and `:pipe` sends it through `td` and puts the result in its place,
  so the change shows at once and unsaved edits are kept. `td` writes other
  files (todo.md, a task file's heading, the agenda) itself.
- **Status keys and `x`** then run
  `:earlier %sh{[ %{buffer_name} -ef ~/.cache/td/agenda.md ] && echo 1 || echo 0}`
  and `:update`. A key can't branch, and `:pipe` always marks the buffer
  modified, even when the line comes back the same. On the agenda, td has
  already changed the task and rebuilt `agenda.md`, so `:earlier 1` takes
  back the pipe's edit, `:update` has nothing to save (the read-only file
  is never written), and Helix's auto-reload shows the rebuilt agenda. In
  any other file `:earlier 0` changes nothing (it says "Already at oldest
  change" until the save's "written" replaces it) and `:update` saves.
  On the agenda `td` gives the line back with a space added before its
  newline, so the pipe always makes exactly one edit for `:earlier 1` to
  take back: a line given back as it was can make none (the empty last
  line does), and the undo would then take back the agenda's last reload,
  leaving it stale and modified. `:pipe` puts anything printed on stderr in place of the
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
- **`+`, `-`** also run the conditional undo, for the agenda and the week
  view: `:earlier 1` there (with the same one-edit rule as the status
  keys), `:earlier 0` anywhere else. On the week view `td` has `tl` rewrite
  it for the week before or after (the week is read from its first line),
  and auto-reload shows it. They don't save, so nothing replaces
  "Already at oldest change": a final `:echo ''` clears it (a bare `:echo`
  is an error).
- **`a`, `A`:** `td list` runs inside `%sh{}`, so the agenda is rebuilt
  before `:open`, and `:reload` drops anything typed into the read-only
  buffer.
- **`i`, `I`** read the task files on disk, so the running entry must be
  there: both save the new entry at once. They end the running entry in
  its own buffer, not on disk, so a note typed there and not yet saved is
  kept (writing that file behind Helix's back would clash with it). In
  order:
  1. `:open %sh{tl running --from …}` goes to the file with the latest
     running entry (this buffer if nothing runs); `tl` keeps this
     buffer's name in `~/.cache/tl/from`.
  2. That whole buffer goes through `:pipe tl stop -`, and `:update` saves
     it.
  3. `:open %sh{tl next --skip …}` (`I`: `tl next --back`) ends what still
     runs in the other files on disk and goes where you clock in: back to
     the buffer kept in step 1 (`i`), or the task before the running one
     (`I`). On disk that entry still runs, since the save lands later, so
     `tl` can tell which task was current.
  4. `tl start`'s output goes on a new last line, and `:write!` saves it.
     The `!` is needed when this is the buffer step 2 saved: a second save
     of one buffer in one key otherwise fails with "file modified by an
     external process", since Helix hasn't recorded the first one yet.
- **`q`** opens todo.md and pipes its first line through
  `td new - --above`, which prints that line back with `- [ ] ` on a line
  above it, or just `- [ ] ` when the line already is that empty bullet.
  `goto_file_start` then lands on the bullet either way, and
  `insert_at_line_end` types after it. It can't add the line with
  `open_above` and `:insert-output td new`, as `i` does with `tl start`
  and `open_below`: languages.toml makes `- [ ]` a markdown comment
  token, so opening a line next to a `- [ ] …` one already starts it with
  `- [ ] `, and the key gave `- [ ] - [ ] `. Enter continues a bullet the
  same way, which is how an empty `- [ ] ` gets left behind. A Helix key
  has no if, so the check has to be in a command that gets the line.
- **`Q`** does the same with the last line: `goto_last_line` and
  `td new -`, which puts the bullet under the line instead.
- **`space`** repeats `q`'s command list, as a key can't name another.
- **`n`** is a macro too, ending at the prompt
  `:open %sh{td file "$BASH_EXECUTION_STRING" # name: }` with the cursor
  moved before the `}` (`<left>`), so your text goes inside `%sh{}`. On
  Enter, `td file` creates the file and prints `PATH:2`, which `:open`
  opens. The name is a shell comment read back from
  `$BASH_EXECUTION_STRING`, as `o` does it; a `}` in it would end `%sh{}`
  early.
- **`N`** is a macro that copies the name from the row: `x` selects the
  line, `S` splits it on the parts around the name (the leading `- [S] `,
  a trailing `  ~/tasks/f.md:1:1` or ` (*)`, and the newline), `)` and `,`
  keep just the name, and `"ty` copies it into register `t`. Then `;`, the
  prompt `:open %sh{td rename --from … "$BASH_EXECUTION_STRING" # name: }`,
  `<left>` and `Ctrl-r t` paste it before the `}`. On Enter, `td rename`
  reads the row from `agenda.md` on disk (never edited, so it matches),
  renames, rebuilds the agenda and prints `AGENDA:LINE` to stay on.
  Getting the name another way doesn't work: switching buffers inside the
  key (a scratch buffer, or a file holding the name) closes the prompt as
  soon as the key ends.
- **`o`** is a macro, so the command prompt stays open for you to type.
  The prompt holds `:sh tl out "$BASH_EXECUTION_STRING" # done: `, so what
  you type is a shell comment, which bash ignores. `tl` reads it back from
  `$BASH_EXECUTION_STRING` (the whole command line), so it needs no
  quoting. `tl` looks for exactly `"$BASH_EXECUTION_STRING" # done:`
  (`DONE_MARK` in `tl`): change both together.
- **`O`** can't switch buffers before its prompt: a key that does loses
  the prompt as soon as it ends (see `N`). So `tl out --back` does the
  switch on disk first, under `:noop %sh{}`: it ends the entries, adds the
  new one to the other task's file, and keeps what it did in
  `~/.cache/tl/switch`. `:reload-all` brings both files into their
  buffers (`:write-all` saved them, so nothing is lost). The prompt is
  `:open %sh{tl note "$BASH_EXECUTION_STRING" # done: }`, with the cursor
  before the `}`, as `n` does: on Enter, `tl note` adds the heading and
  prints the new entry's `PATH:LINE:COL`, and `:open` goes there. That
  buffer is up to date already, so the cursor lands on the new line.
- **`l`** runs `align_view_top` first: a popup opens below the cursor's
  screen row when 6 rows fit there, so at the top it gets the full height.

### Why `p` and `P` are separate

Bullets carry no link to their file: it is found from the bullet's text. If
one key both jumped and created, a typo would make a stray file
(`refacror td parser` → `refacror-td-parser.md`). So `p` only goes where
something exists, and `P` (capital: more deliberate) is the one that
creates.

### To do: one key for a task's own file

`P` and `n` both end in a task's own file: `P` gives the bullet under the
cursor its file (on an agenda row, it opens the row's file), and `n` asks
for a name and makes a new file task. They should become one key that acts
by context: on a bullet or an agenda row, open or create its file;
anywhere else, ask for a name.

Helix keys can't do that yet. A binding is either a list of commands that
always all run (`P`) or a typed sequence that can stop at the command
prompt (`n`), never one or the other depending on where the cursor is.
Merging them now would make `P` always stop at the prompt: an extra Enter
on every promote, and a name prompt where none is needed. It becomes simple
with the `:eval` idea in
[td-plan.md](td-plan.md#future-directions--integration-with-helix), if
`:eval` can also run a typed sequence: the key asks `td` first, and `td`
answers "open this file" or "ask for a name".

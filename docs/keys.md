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
from the times. todo.md is a task file too, but its todos (`- [S] ` lines)
are never entries, even one that starts with a date and time: there the
entries go under the todos (see [Time in todo.md](#time-in-todomd)).

| Key | What it does |
|---|---|
| `i` | **Clock in.** First ends what is running (every entry that has no end, however long ago it started), in whichever task file it is, keeping a note you typed there and haven't saved; that file is saved. Then adds `YYYY-MM-DD HH:MM - ` on a new line at the end of this buffer, saves it so the next clock-in can find the entry, and leaves you in normal mode at its end: `a` (or `A`) types the note. In todo.md it goes under the todo you are on instead, at the end of its section (its notes, up to the next todo); above the first todo, on a new line below, or on the line itself if it is blank (see [Time in todo.md](#time-in-todomd)) |
| `I` | **Go to the running entry.** Opens the task file with the running entry (the latest started, in any task file) with the cursor on it, and shows "running since HH:MM". The cursor goes by the line the entry has in the buffer, so a todo added above it and not saved yet doesn't move the cursor off it. Changes nothing. With nothing running it stays where you are and shows "nothing running" |
| `L` | **Week summary in a buffer**, to copy from. Saves, then opens `~/.cache/tl/summary.txt` with the same report as `l`, for this week, Monday to Sunday, over all task files (wherever you press it). The file is rewritten each time and read-only, like the agenda; anything typed there is thrown away by the next `L`. In it, `-` and `+` show the previous and next week, as often as you press them; `L` goes back to this week |
| `o` | **Clock out and write it down.** Ends the running entry (the latest started, in any task file) and goes to its task file, in insert mode on a heading right above the entry: a new `# `, or ` - ` added to the heading already there. Type what you did; it is the entry's heading, as `O`'s prompt makes it, and saving keeps it. The entry is ended in its own buffer, so a note typed there and not yet saved is kept, and that file is saved. Esc leaves the empty `# ` (or ` - `); the next `o` there uses the `# ` as it is. In todo.md too: the heading goes above the entry there as well (see [Time in todo.md](#time-in-todomd) for what that does to the todo's section). With nothing running, it stays on your line, in insert mode at its end (Esc). An entry is running however long ago it started, but an entry has no end date: one left open for more than a day is ended with the time of day only, so its duration counts just the hours past the last whole day (fix the end by hand, then `u`) |
| `O` | **Clock out from here.** Saves all buffers, then waits at the command prompt `# done: `, without leaving this buffer. Type what you did and press Enter: the latest running entry (in any task file) gets its end time and duration, and your text becomes the `# heading` line right above it, or is added to the heading already there after ` - `, in todo.md too. Enter on an empty prompt ends the entry with no heading; Esc does nothing. The text needs no quoting; only `%` is special (type `%%` for one) |
| `u` | **Refresh durations.** After you change an entry's start or end time by hand, works its `= 1h 15min` out again from the times. Acts on the entry on the cursor's line, or on every entry in the selected lines (`%` first for the whole file); other lines are left alone. An entry still running there gets its end time now, as if clocked out with no heading. In todo.md the todos themselves are left alone. Doesn't save. (`+`/`-` on a time refresh the duration by themselves) |
| `r` | **Recent files.** A popup with the 9 most recently changed task files, newest first, each with its last entry. Open one with `:o <path>` |
| `l` | **Summary** (time log). Saves, then shows time per day for the last 14 days in a popup: per task file its total and title, and under it the `# headings` it was worked under. Running entries come first, and problems (overlaps, duplicates, typos, entries over 12 hours) last, as `~/path:line` you can open with `gf`. Always over all task files, wherever you press it (the agenda too) |

### Time in todo.md

A todo you jot notes under and work on before it deserves a file of its
own:

```
- [ ] prep slides

check last year's deck
2026-10-21 14:37 - 15:10 = 0h 33min  made outline
2026-10-21 16:00 -

- [ ] call mom
```

- A todo's **section** is the lines under it, up to the next todo at its
  indent or less, or a heading; blank lines at its end are left out.
  A heading right above a time entry (the one `o` and `O` add) is part of
  the section, with its entry; a heading with anything else under it ends
  it. Notes need no indent. A sub-todo (`  - [ ] print`) has a section of its
  own inside its parent's, which ends at a line indented less than the
  sub-todo: so a note back at the left after it is the parent's again.
- `i` on the todo, or anywhere in its section (a blank line after it
  counts), adds the entry at the end of the section, lined up with the
  todo. `tl` writes the line, so Helix doesn't start it with `- [ ] `.
  Above the first todo, or under a heading with no todo yet, it goes on
  the line if it is blank, else on a new line below.
- `o` and `O` put what you did in a `# heading` right above the entry, as
  in any task file. The heading stays in the todo's section, so `i` on it
  or on its entry, `P` and `Enter` treat the pair as part of the todo.
  The heading is a line at the left, even above an indented entry; for a
  sub-todo's section the entry's indent decides whether the pair is in.
- In the summary, todo.md is `todo`, with no title, and the entries come
  under the text of the todo whose section they are in; an entry with a
  heading right above it comes under that heading instead (what you did),
  and an empty `# ` doesn't count.
- `P` on the todo moves its section to its file (see `P` below):
  sub-todos come out as the file's subtasks, and `tl` finds a running
  entry there.
- The agenda and the reminders never see these lines: td reads only the
  todos in todo.md. If you delete a todo by hand, delete its section with
  it, or its time ends up under the todo above.

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
| `N` | **Rename a task**, from its agenda row, or from inside its own file `~/tasks/<slug>.md`. Opens the command prompt at `# name: ` with the task's current name filled in (in the file, the title of its first-line `# [S] title` heading: the cursor goes to that line, and the file is saved first); edit it, or delete it and type a new one, then press Enter (Esc does nothing). The new name goes through the same check as `n`'s, and the task changes where it lives: a file task's (or orphan's) file is renamed to the new name's slug and its first-line heading gets the name, keeping its `[S]`; a bullet row's todo.md bullet gets the name as its text, and its own file, if any, is renamed and retitled with it, so the two stay linked. The agenda reloads, and the task keeps its place in it. Inside the file the new name opens in its place: the heading, the file name and the todo.md bullet that owns the file change together, and the bullet keeps its stamps and repeater (the prompt shows the heading's title, which has none). Refused, changing nothing, when a file already has the new name, the name has no letter or digit, or the row shows no task (a subtask row: `p` to it and edit it there). As with `n`, `%` is typed `%%`, and the name can't contain `}`. Don't rename a file you have open in another buffer: that buffer keeps the old name (in the file itself too: close the old buffer, `:bc`, after the new one opens) |
| `a` | **Agenda.** Opens a snapshot of todo.md grouped TODAY, ACTIVE, TODO, WAITING, newest-added first; done and ignored bullets are hidden. After TODAY, under RESCHEDULE, the reminders that went off while their task is still open (not those on a line with a `++`/`.+` repeater), each pointing at its date: `p` there to move it with `+`/`-`. A bullet with its own file shows ` (*)`, and under an open task with its own file, indented, come the file's open subtasks (its `[ ]`, `[Y]`, `[A]` and `[W]` bullets), folded under it as `⋯ N lines`: `za` on the task's row unfolds them and folds them again, `zR` unfolds all, `zM` folds all. Each `a` folds them all again; a status key keeps a task you unfolded open. Files without a bullet are listed by the status on their first line (`# [W] renew passport`), or under ORPHANS if they have none; their rows end in ` (*)` as well. View only: Helix shows `[readonly]`, and anything typed there is thrown away by the next `a`. But `x` and the status keys work on its rows: they change the task itself (see below), and the agenda reloads. `q` adds a new task, `n` a new file task, and `N` renames the task on a row. For anything else, `p` takes you to the task |
| `A` | The same agenda, most recently changed first: a bullet's line (state, text, stamp) or its own file. Edits by hand count from the next `a`, `A` or status key |
| `D` | **Done tasks.** The agenda with only the done ones under DONE: `[x]` bullets and files whose first line is `# [x] title`, most recently changed first, as `A` orders them. `x` on a row takes the task back to `[ ]` and the row drops out; `p` goes to the task. `a` brings back the open ones |
| `p` | **Go to the task.** On a bullet: open its own file, if it has one; otherwise stay. On an agenda row: go to that bullet's line in todo.md; a row for a file goes to the file; a subtask row goes to its line in the task's file; a RESCHEDULE row goes to the reminder's line, the cursor on its day. Never creates anything. Uses the line as it is in the buffer, saved or not |
| `P` | **Give the task a file.** Creates `~/tasks/<slug>.md` for the bullet, with a heading `# [S] title` that carries the bullet's state (the title leaves out the bullet's stamp and repeater, and the brackets around them, so `[… 09:50 ++1h]` doesn't leave a `[ ]` in the name or the file name: the reminder stays on the bullet), and opens it. In todo.md the bullet's section (its notes and time entries: the lines under it, up to the next todo) moves to the end of the file, without the indent its lines share, and the bullet stays as the link; todo.md is saved. An existing file is reused, its heading's state updated, and gets them at its end. On an agenda row it only opens the row's file, if any. Works on a bullet you have just typed, saved or not |
| `Enter` | **Move to day.md.** Moves the bullet on the cursor's line, with its section (its notes, time entries and sub-todos: the lines under it, up to the next todo not under it or a heading, one right above a time entry excepted), to the end of `~/tasks/day.md`, and saves the buffer; the cursor stays on the line the bullet was on. The bullet's indent comes off, so a sub-todo lands at the left. It works in any task file, from the buffer as you have it, saved or not. In day.md, blank lines at the end are dropped first, and a heading last there gets one blank line under it (day.md needs none: a missing or empty one just gets the bullet). Does nothing on a line that is not a bullet, in day.md itself, or on the agenda. A reminder on the bullet keeps working, but it fires under the file's title (its first `# heading`, else `day`), not the bullet's text; and the agenda, which reads only todo.md, no longer lists the bullet |
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
  row, that file's `# [S] title` heading, or, on a subtask row, its line
  in the task's file, as the key does there. Then the agenda is rebuilt, in
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
  first.) `td promote` also keeps an inbox bullet's place, and its file,
  in `~/.cache/td/cut`. `P` then pipes the whole buffer through `td
  promote --cut -`: in todo.md that takes the bullet's section out of the
  buffer and adds it to the file on disk; anywhere else the text comes
  back as it was. Then the conditional undo and `:update`, as the status
  keys do: on the agenda `:earlier 1` takes the pipe back and nothing is
  saved; anywhere else `:update` saves, so todo.md is saved before you
  leave it (`td` writes it when you change the state in the new file).
- **`ret`:** built like `P`: `:pipe-to` sends the bullet's line to `td day`,
  which keeps its place in `~/.cache/td/day`, then `td day --cut -` takes
  the whole buffer and returns it without the bullet and its section, which
  it has added to day.md on disk. `select_all` and `:pipe` leave the cursor
  at the end of the buffer, so `td` also writes the line the bullet was on to
  `~/.cache/td/open`, and the key ends with `:open` of it, as `P` does, to put
  the cursor back. Nothing is kept when the line is not a bullet, so the text
  comes back as it was.
  The section goes to the file on disk, not its buffer: a pipe in that
  buffer would move its cursor to the end even with nothing to add.
  Auto-reload then shows it in the file's buffer, if you have it open. With
  unsaved edits there, Helix refuses to save them over the change on disk:
  `:w!` would drop the moved lines, so copy your edits over first.
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
- **`i`** reads the task files on disk, so the running entry must be
  there: it saves the new entry at once. It ends the running entry in
  its own buffer, not on disk, so a note typed there and not yet saved is
  kept (writing that file behind Helix's back would clash with it). In
  order:
  1. `:open %sh{tl running --from …}` goes to the file with the latest
     running entry (this buffer if nothing runs); `tl` keeps this
     buffer's name and the cursor's line in `~/.cache/tl/from`.
  2. That whole buffer goes through `:pipe tl stop -`, and `:update` saves
     it.
  3. `:open %sh{tl next --skip …}` ends what still runs in the other files
     on disk and goes back to the buffer kept in step 1.
  4. That whole buffer goes through `:pipe tl start -`, which adds the
     entry (on a new last line; in todo.md, under the todo the cursor was
     on) and writes its line to `~/.cache/tl/goto`. `:write!` saves it,
     and `:open %sh{cat ~/.cache/tl/goto …}` puts the cursor on it. The `!`
     is needed when this is the buffer step 2 saved: a second save of one
     buffer in one key otherwise fails with "file modified by an external
     process", since Helix hasn't recorded the first one yet. The pipe
     moves the cursor to the end, hence the goto. (The line used to be
     added with `open_below` and `:insert-output tl start`, but in
     todo.md `open_below` starts it with `- [ ] `, which makes it a todo:
     see `q`.)
- **`I`** goes in three steps, like `o`, because the line the entry has on
  disk is not always the one it has in the buffer (todo.md, where the entry
  sits mid-buffer, in a todo's section, has unsaved edits above it more
  often than a task file, whose entry is last; a new todo from `q` is one):
  1. `:open %sh{tl where --visit --from …}` opens the file of the latest
     running entry, and `tl` keeps its path and line on disk in
     `~/.cache/tl/goto`. With nothing running it prints the buffer the
     key was pressed in, and keeps the line, so `:open` stays there: a
     failing `%sh{}` would hand `:open` nothing, and Helix would show its
     own error ("path must be a regular file") instead of `tl`'s.
  2. `select_all`, then `:pipe-to tl where --locate - --file …` sends that
     buffer to `tl`, which writes its running entry's line there instead
     (`:pipe-to` leaves the buffer alone, and unsaved).
  3. `:open %sh{cat ~/.cache/tl/goto …}` goes there, then
     `:echo %sh{tl where --say}`.
- **`q`** opens todo.md and pipes its first line through
  `td new - --above`, which prints that line back with `- [ ] ` on a line
  above it, or just `- [ ] ` when the line already is that empty bullet.
  `goto_file_start` then lands on the bullet either way, and
  `insert_at_line_end` types after it. It can't add the line with
  `open_above` and `:insert-output td new`: languages.toml makes `- [ ]` a markdown comment
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
  `$BASH_EXECUTION_STRING`, as `O` does it; a `}` in it would end `%sh{}`
  early.
- **`N`** is a macro that copies the name from the row. It starts with
  `:update` (a write lands once the macro ends, while you type the name,
  so a task file's unsaved edits are on disk before `td` moves it) and
  `:open %sh{td rename --focus …}`, which prints `PATH:1` inside a task
  file, so the cursor lands on its heading, and the line you were on
  anywhere else. Then `x` selects the
  line, `S` splits it on the parts around the name (the leading `- [S] `
  or `# [S] `, a trailing ` (*)`, and the newline), `)` and `,`
  keep just the name, and `"ty` copies it into register `t`. Then `;`, the
  prompt `:open %sh{td rename --from … "$BASH_EXECUTION_STRING" # name: }`,
  `<left>` and `Ctrl-r t` paste it before the `}`. On Enter, `td rename`
  reads the row from `agenda.md` on disk (never edited, so it matches),
  renames, rebuilds the agenda and prints `AGENDA:LINE` to stay on. From a
  task file it reads the file on disk instead, renames file, heading and
  bullet, and prints the new path for `:open`; the old buffer stays open
  under the old name, unmodified, so nothing writes the old file back.
  Getting the name another way doesn't work: switching buffers inside the
  key (a scratch buffer, or a file holding the name) closes the prompt as
  soon as the key ends.
- **`o`** works like `i`: it ends the entry in its own buffer, not on
  disk, so unsaved edits there are kept. (Ending it on disk inside one key
  can't keep them: `:write-all` only lands after the key, so `tl` would
  edit the old file, and the reload that shows its change drops the
  buffer's edits.) In order:
  1. `:open %sh{tl out --visit --from …}` goes to the file with the latest
     running entry (this buffer if nothing runs); `tl` keeps this
     buffer and line in `~/.cache/tl/goto`.
  2. That whole buffer goes through `:pipe tl out --edit -`, which ends its
     latest running entry, adds the `# ` (or ` - `) heading, and writes the
     heading's line to `~/.cache/tl/goto`; `:update` saves it. This is the
     same in todo.md.
  3. `:open %sh{cat ~/.cache/tl/goto …}` goes there (or back, if nothing
     ran), and `insert_at_line_end` types after it. A key has no if, so
     with nothing running it still ends in insert mode.
- **`O`** is a macro, so the command prompt stays open for you to type.
  The prompt holds `:sh tl out "$BASH_EXECUTION_STRING" # done: `, so what
  you type is a shell comment, which bash ignores. `tl` reads it back from
  `$BASH_EXECUTION_STRING` (the whole command line), so it needs no
  quoting. `tl` looks for exactly `"$BASH_EXECUTION_STRING" # done:`
  (`DONE_MARK` in `tl`): change both together.
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

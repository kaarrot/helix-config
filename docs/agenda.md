# agenda — `td` + `tl` design

Two companion scripts in this folder, both pure Python stdlib, both without
config files (env vars and defaults):

- `tl` — time log: clock in and out of task files, summaries
- `td` — todos: the inbox, task files, reminders, the agenda

Every key, and why each is built the way it is, is in [keys.md](keys.md).
This file is the design.

## Quick start

Tasks, the agenda and `tl` work anywhere. Reminders need Termux on Android.
The first time:

1. **Termux:API**: install the Termux:API app from the same place as
   Termux (F-Droid), and its commands: `pkg install termux-api`. Check that
   `termux-notification -c hello` shows a notification.
2. **Build tools** for the alarm helper: `pkg install ecj dx` (about 10 MB;
   both run on Android's own Java runtime, so no JDK).
3. **Battery**: in Android's settings, set Termux and Termux:API to
   *Unrestricted* (Apps → Termux → Battery). On Samsung, also add both to
   *Never sleeping apps* (Battery → Background usage limits) and turn off
   *Put unused apps to sleep*, which stops a sleeping app's alarms.
4. **Install**: `~/.config/helix/bin/td install`. It builds
   `bin/TdAlarm.java` into `~/.cache/td/td-alarm.jar`, writes the `td-tick`
   shim, cancels the 15-min job older versions used, and arms the next
   reminder. Re-run it whenever `bin/TdAlarm.java` changes.
5. **Try it**: add `- [ ] test 2026-10-14 18:05` to todo.md, with a time a
   few minutes ahead, save, open the agenda (`space , a`, which arms the
   alarm), and lock the screen. The notification arrives at that minute. If
   it doesn't, `~/.cache/td/alarm.log` says why the alarm wasn't set, or run
   `td tick` in a shell to see it.

Off Termux, `td tick`, `install`, `uninstall` and `fire` refuse and say
so; `TD_TERMUX=1` forces them on (see [Environment](#environment)).

## Tasks

### The inbox

`$TD_FILE` (default `~/tasks/todo.md`) holds one bullet per task. The
character in the checkbox is the state:

| state | checkbox |
|-------|----------|
| todo | `[ ]` |
| today | `[Y]` |
| active | `[A]` |
| waiting | `[W]` |
| done | `[x]` |
| ignore | `[!]` |

```
- [ ] call jon
- [Y] pay rent 2026-11-01 Sun 09:00 ++1m
- [A] refactor td parser
- [W] reply from bank
- [x] took bins out
- [!] call mom
```

Lowercase `[y]`, `[a]` and `[w]` read the same; `td` writes the uppercase
form when it changes a line. todo.md is the source of truth: the agenda is
a view of it.

### Task files

A task can have its own notes file in `$TL_DIR` (default `~/tasks`),
created by `space , P`:

```
# [A] refactor td parser

2026-11-01 10:00

- outline the parser rewrite
- benchmark old vs new
```

The heading carries the task's state, kept in step by the status keys (see
[keys.md](keys.md#status-keys-in-other-files)). There is no link in the
bullet: the file is named after the bullet's text, its *slug*: lowercase,
every run of other characters turned into one `-`, and a trailing stamp and
repeater left out.

- `Costco run!` → `costco-run.md`
- `costCo RUN` → `costco-run.md` (the same file)
- `pay rent 2026-11-01 Sun 09:00 ++1m` → `pay-rent.md`

An existing file is reused, never overwritten or numbered. Renaming a
bullet unlinks it from its file: the file then shows on the agenda as a
file task or an orphan (below), and `space , p` no longer finds it.

### File tasks

A long-lived or clearly defined task can live in its file alone, with no
todo.md bullet: give the file a status on its first line,
`# [W] renew passport`. `space , n` creates one from a name you type, with
`# [ ] name` on the first line, and `space , N` on its agenda row renames
it (file and heading). Every name, new or changed, goes through the same
check: whitespace tidied, and a letter or digit needed for the file name. The agenda
lists it under that status (`[x]`/`[!]` hide it), with the file's path so
`space , p` opens it. A file with a todo.md bullet follows the bullet
instead. A file with neither is an orphan.

### Time-log entries and reminders

`tl` and `td` both read lines that start with a date and a time. The dash
decides whose a line is:

```
2026-10-13 09:30 - 10:45 = 1h 15min  note     a time-log entry (tl)
- [ ] 2026-10-13 13:00 -                      a running time-log entry (tl)
2026-11-01 10:00                              a reminder (td)
- [ ] call bank 2026-10-12 10:00 - bring docs a reminder (td): the dash is not right after the start
```

A line that starts with date, time and a dash (after an optional `- `, `* `
or a checkbox in any state, `- [ ] `, `- [Y] `, ...) is a time-log entry:
`td` never fires its leading time, and `tl` logs it, or flags it under
"Check by hand" if it is malformed. Any
other date and time is `td`'s. Both scripts use the same pattern (`tl`'s
`ATTEMPT`, `td`'s `TL_ENTRY`), and `td test` checks they still match.

`tl` doesn't read todo.md at all, but `td` applies the rule there too: a
bullet that starts `- [ ] 2026-10-12 09:00 - …` doesn't fire. Put the stamp
after the text.

## Reminders

### What fires

Any `YYYY-MM-DD HH:MM` (a weekday between them, `2026-11-01 Sun 10:00`, is
allowed and ignored) fires a Termux notification:

- in todo.md, on a bullet that is open: `[ ]`, `[Y]`, `[A]` or `[W]`
- in `~/tasks/*.md`, on any line, while the file's todo.md bullet is open,
  but on a subtask that is done or ignored (`- [x] book taxi 2026-10-20 10:00`).
  A bullet marked done by hand, or with `space . x`, stops its file too,
  whatever the heading says. A file with no bullet fires unless its first
  heading is `# [x]`, `# [X]` or `# [!]`.

Except the leading time of a time-log entry (above).

### When it fires

At the stamped minute, minus the lead time `TD_LEAD_MIN` (default 0). An
exact Android alarm wakes `td tick` then (see below), and the notification
arrives within about a second, with the screen off too.

A time fires once it is due if a tick saw it in the future (it is then in
`~/.cache/td/scheduled`), **or** if it was still to come at the previous
tick, that is, it was added since then (the previous tick's time is in
`~/.cache/td/last-tick`). So:

- A reminder added a few minutes before it is due fires on the next tick.
- Old dates in notes never fire: they were already past at the previous
  tick. On the very first tick nothing past fires.
- A `space , s` stamp of "now" never fires: `td stamp` records the times it
  writes that are already due (`~/.cache/td/stamped-now`), and the tick
  skips them. Edit the stamp to a later time and it fires as usual.
- The price: a time typed by hand after it passed, but after the previous
  tick (a note like "called 10:05" written at 10:10), fires once.
- A reboot clears the alarm. The next tick (opening the agenda is enough)
  fires what came due meanwhile, late, and arms the alarm again.
- A stamp with a `++`/`.+` repeater fires again every N units while its
  task is open (see [Recurring tasks](#recurring-tasks)).

Each reminder (its file, time and line text) fires once
(`~/.cache/td/fired`). Editing the time makes it a new reminder. Two
reminders at the same minute both fire, even in one file. A state change
(`[ ]` → `[Y]`) or a repeater bump keeps the text, so a reminder that has
fired doesn't fire again. A notification that fails isn't counted as
fired: it is retried a minute later. A reminder that fired stays on the
agenda, under RESCHEDULE, until you move its date or finish the task,
unless its line has a `++`/`.+` repeater: that one reminds you again at
its next time instead.

### How it runs

```
  td list, td edits                Android alarm (exact, owned by Termux)
  (in the background)                     │
         │                                ▼
         └──────────────▶ td tick ◀── td-tick --alarm
                             │
              scan ~/tasks/*.md, fire what is due ──▶ termux-notification
                             │
                             ▼
              arm the alarm for the next reminder
```

There is one alarm, set for the earliest reminder still to come (its time
minus the lead) that hasn't fired. Every tick works it out again from the
files, so adding, moving or closing a reminder just moves the alarm, and
td keeps no list of alarms to keep in step. When the alarm goes off, its
tick fires what is due and arms the next one, so the chain walks through
every reminder in order.

The alarm comes from `bin/TdAlarm.java`, which `td install` builds into
`~/.cache/td/td-alarm.jar` (see [Quick start](#quick-start)). td runs it
under `/system/bin/app_process` as Termux, the way Termux's own `am`
command runs, and it asks Android's alarm service for a
`setExactAndAllowWhileIdle` alarm owned by Termux: exact to the second,
allowed while the phone sleeps, and with no status-bar icon. Termux targets
an old Android version (SDK 28), so Android 12 asks for no exact-alarm
permission. When the alarm goes off, Termux runs the shim in the background
with `--alarm`. 15 s before that, a second alarm makes Termux take its wake
lock, so the phone can't fall asleep while the tick posts the notification.
The tick then releases it with `termux-wake-unlock`, which also releases a
wake lock you took yourself.

A tick also runs in the background, 2 s after `td list` (the agenda keys)
and the commands that change tasks on disk, or whose key saves next:
`toggle`, `set`, `rename`, `file` and `promote`. So the alarm follows the
status keys, `n`, `N` and `P`, and opening the agenda re-arms it after a
reboot. The 2 s let a key's trailing `:update` save the buffer first, and
running in the background hides the helper's ~1.3 s start-up.

A plain `:w` after a hand edit runs no tick: open the agenda to arm it (or
run `td tick`). The same goes for `space , s`, `+`, `-` and `space , q`:
they don't save, so a tick after them would only see the file as it was.
Ticks take `~/.cache/td/tick.lock`, so two at once never fire a reminder
twice.

The shim is `~/.config/helix/bin/td-tick`, which `td install` writes:

```sh
#!/bin/sh
exec /data/data/com.termux/files/usr/bin/python3 /data/data/com.termux/files/home/.config/helix/bin/td tick "$@"
```

It holds no settings (a tick from the alarm doesn't see `.bashrc`
exports): the defaults live in `td`, so re-running `td install` changes
nothing else. Older versions ran it from a 15-min JobScheduler job (id
7421); `td install` cancels that job. `td uninstall` cancels the alarm and
removes the shim.

Each tick:

1. **Scans** `$TL_DIR/*.md`, plus `$TD_FILE` if it lives elsewhere, for the
   times that can fire (above).
2. **Records** each time not yet due (minus the lead) in `scheduled`.
3. **Fires** each time that is due (minus the lead), not yet in `fired`,
   and in `scheduled` or added since the previous tick, then adds it to
   `fired` and saves this tick's time in `last-tick`.
4. **Arms** the alarm for the earliest time still to come, or a minute from
   now when a notification failed, or cancels it when nothing is left. A
   failure to arm goes to `alarm.log`, and `td tick` in a shell prints it.

The notification is titled `TODO`. Its text is the bullet's text, or the
task file's first heading (its name if it has none). It plays the
notification sound, and tapping it opens the file (needs the Termux:API
app).

## The agenda

`space , a` writes `~/.cache/td/agenda.md` and opens it:

```
# td VIEW ONLY (status keys change the task itself; space , p goes there): [ ] todo  [Y] today  [A] active  [W] waiting

# TODAY

- [Y] pay rent

# RESCHEDULE

- call jon [2026-10-15 Thu 10:00]  ~/tasks/todo.md:3:25

# ACTIVE

- [A] refactor td parser (*)

# TODO

- [ ] call jon [2026-10-15 Thu 10:00]

# WAITING

- [W] renew passport  ~/tasks/passport.md:1:1

# ORPHANS

- old-task  ~/tasks/old-task.md:1:1
```

- RESCHEDULE rows, after TODAY, are reminders that went off and still
  wait: the task is open and the date unchanged. A line with a `++`/`.+`
  repeater isn't listed: it reminds you again at its next time. A
  row is the reminder's line (`trip: book taxi 2026-10-20 10:00` for one in a task file), oldest
  first, ending in `path:line:col` with the column on the date's day. So
  `space , p` puts the cursor there, for `+`/`-` to move the date (or
  `space , s` to set it to today); if the file changed since the agenda
  was built, it finds the line again. A row goes once its date is in the
  future again or its task is done. The task keeps its row in its group
  too, and that row takes `space , x` and the status keys: RESCHEDULE rows
  have no checkbox, so those keys pass them by. Only `space , a` and
  `space , A` show RESCHEDULE.
- Bullet rows are todo.md's open bullets, ` (*)` when the task has its own
  file. They carry no path: `space , p` finds the row's line in todo.md
  (same state and text). If todo.md changed since the agenda was built and
  nothing matches, it stays put; `space , a` rebuilds.
- File-task rows (listed under their status) and orphan rows (files with
  no bullet and no status) end in `path:line:col`, so `space , p` or `gf`
  opens the file.
- Order within a group: newest added first (`space , a`; when `td` first
  saw the task, in `~/.cache/td/added`), or most recently changed first
  (`space , A`; the bullet's line in `~/.cache/td/changed`, or its file's
  modification time).
- `space , D` lists the done tasks instead, under `# DONE`: `[x]` bullets
  and file tasks whose heading is `# [x] title`, most recently changed
  first. The keys work on its rows as on the agenda's: `space , x` takes a
  task back to todo.

The agenda is a view: it is always built from todo.md and the task
files, never edited. `td` writes it read-only (0444), replacing it by a
rename so Helix still reloads it; Helix shows `[readonly]` and refuses
`:write`.

The status keys and `space , x` still work on its rows, by changing the
task where it lives: a bullet row sets its todo.md bullet (and its own
file's heading follows), a file-task row sets that file's `# [S] title`
heading. Then `td` rebuilds the agenda with the options it was opened
with (`~/.cache/td/agenda-args`, so `space , A`'s order stays), and Helix
reloads it; the row itself is never written. `+`, `-`, `space , s` and
`space , P` leave rows and tasks alone. `space , q` (or `space , space`)
adds a new task at the top of todo.md, `space , Q` at the end. For anything else, `space , p` to the task. How the keys manage this is in
[keys.md](keys.md#how-the-keys-are-built).

## Recurring tasks

A repeater after the stamp, `++Nu` or `.+Nu` (N ≥ 1, u = `h`|`d`|`w`|`m`|`y`),
makes a bullet repeat. Marking it done (`space , x`) moves the date instead
and keeps it `[ ]`; the rest of the line is kept.

```
- [ ] pay rent 2026-10-01 Thu 09:00 ++1m        # → 2026-11-01 Sun 09:00
- [ ] water plants 2026-09-15 Tue 07:30 .+2w    # → today + 2 weeks, 07:30
- [ ] standup 2026-10-10 Sat 09:00 ++1w         # weekly at the same hour
```

| repeater | new date |
|----------|----------|
| `++Nu` | **anchored**: old date + N units, repeated until it is after now. Missed cycles don't pile up, and "rent on the 1st" stays on the 1st however late you tick it |
| `.+Nu` | **floating**: today + N units, at the stamp's time. "Water the plants about 2 weeks after I last did" |

Until you mark it done, it reminds you again at each of its times: the
date, the date + N units, + 2N, and so on.
`pills 2026-10-10 Sat 12:00 ++1d` left open fires again on the 11th at
12:00, and every day after.
`td` never writes the file for this (it works the times out on each tick),
so a buffer with unsaved changes is safe. After the phone has been off
for a while, you get one notification for the latest time it missed, not
one for each.

Hours (`h`) are different: `++Nh` is a reminder that repeats every N hours
until done, not a task that comes back, so `space , x` marks it `[x]`
and the date stays.

```
- [ ] stretch 2026-10-16 Fri 09:50 ++1h         # 09:50, 10:50, 11:50... until [x]
```

A task file with no todo.md bullet (a file task) repeats by its own date:
the date and repeater on a line that isn't a bullet, or on the heading.
`space , x` on its agenda row moves every such date in the file, and the
heading stays `# [ ]`; on the date's line it moves that date. Bullets in
the file are subtasks with dates of their own.

```
# [ ] haircut
2026-12-15 Tue 11:50 ++2m                       # → 2027-02-15 Mon 11:50

1mm at the back
```

On the heading inside the file, `space , x` moves only a date on the
heading line: the key gets that line alone, so with the date on another
line it leaves the task as it is.

Months clamp the day: Jan 31 + 1m → Feb 28/29; Feb 29 + 1y → Feb 28. The
repeater must be a word of its own: `C++1d` and `++1days` are text, and so
is `++0d` (it would never move), so those lines are just marked done.
`space . x` ignores repeaters.

## Commands

| command | does |
|---------|------|
| `td install` | build the alarm helper, write the `td-tick` shim, cancel the old job 7421, arm the next reminder |
| `td uninstall` | cancel the alarm (and the old job), remove the shim |
| `td tick` | scan, record future times, fire due ones, arm the alarm for the next one; `--alarm` (from the alarm) also releases the wake lock |
| `td list [--state todo\|today\|active\|waiting\|done\|all] [--sort added\|modified]` | write the agenda to `~/.cache/td/agenda.md` and stdout, and the options to `~/.cache/td/agenda-args` |
| `td promote [--from PATH:LINE]` | stdin: a line. Create or reuse the bullet's task file (not from the agenda), then print where `space , P` goes and write it to `~/.cache/td/open` |
| `td jump [--from PATH:LINE]` | stdin: a line. Print where `space , p` goes and write it to `~/.cache/td/open` |
| `td toggle S [--from PATH [--line N]]` | toggle the line's state between `[ ]` and `S` (a name like `waiting` works too); stdin to stdout, or with `--line` the file on disk. On an agenda row, the task it shows changes instead, and the agenda is rebuilt. Keeps the task's other copies in step (see [keys.md](keys.md#status-keys-in-other-files)); moves a repeating date instead of marking done |
| `td set PATH LINE S` | set the checkbox at `PATH:LINE` to `S` |
| `td stamp [--restamp] [--col N]` | stdin: a line. Add a stamp, or move its date to today keeping the time; `--restamp`, or `--col N` on the stamp, only fixes the weekday |
| `td shift +N\|-N [--col N]` | stdin: a line. Move its stamp by the part under column N (the day without `--col`); on a time-log line, its date, start or end time, in `tl`'s format, duration redone; on the week summary view, the week. With `--col`, save the part's new column to `~/.cache/td/stamp-col` |
| `td new [--state S]` | print `- [S] ` (`space , q` inserts it) |
| `td rename --from AGENDA:LINE NAME` | rename the task on an agenda row: a file task's file and heading, or a bullet's todo.md text and its file (`space , N`) |
| `td file NAME` | create the file task `~/tasks/<slug>.md` headed `# [ ] NAME` (an existing file is left alone) and print the path to open (`space , n`) |
| `td next` | print the next time due (for a status line) |
| `td fire PATH` | fire a file's notification now (testing) |
| `td test [-v]` | run the tests |

## Cache files

Under `~/.cache/td/`. The task files are the source of truth; these only
remember what `td` has seen. Reminders are keyed by (file, time, line text
without its checkbox or stamp), tasks by (file, text without its stamp).

None of them grows for ever. The first tick of each day drops the
`scheduled` and `stamped-now` rows more than 7 days past, and the `fired`
ones too once their reminder has left the open tasks (its date moved, or
the task is done or deleted); until then the agenda can list it under
RESCHEDULE.
A tick has run after those times, so they can't fire again, even if the
reminder is still in a file. `alarm.log` only gets arming failures, so its
lines are kept a year. Building the agenda keeps one `added` and one
`changed` row per task that still exists. The other files are rewritten
each time.

| file | holds |
|------|-------|
| `scheduled` | times a tick saw in the future: `first_seen \t key \t due \t text` |
| `fired` | reminders fired: `due \t key \t text` |
| `last-tick` | when the previous tick ran |
| `stamped-now` | stamps `td stamp` wrote that were already due: `written \t due` |
| `added` | when each task was first seen (the agenda's newest-added order) |
| `changed` | when each bullet's line last changed (`space , A`'s order) |
| `agenda.md` | the agenda, read-only |
| `agenda-args` | the `td list` options the agenda was built with, reused when a change rebuilds it |
| `stamp-col` | the cursor column for `space , s`, `+` and `-` |
| `open` | where `space , p` / `P` go next |
| `td-alarm.jar` | the alarm helper `td install` builds from `bin/TdAlarm.java` |
| `alarm.log` | failures to arm the alarm: `when  could not arm TIME: why` |
| `tick.lock` | held while a tick runs |

## Environment

| var | default | effect |
|-----|---------|--------|
| `TL_DIR` | `~/tasks` | the task folder |
| `TD_FILE` | `$TL_DIR/todo.md` | the inbox |
| `TD_LEAD_MIN` | `0` | fire this many minutes before the stamped time |
| `TL_NOW` | (unset) | fake clock, `YYYY-MM-DD HH:MM`, for tests |
| `TD_DRY_RUN` | (unset) | `1` prints `would fire: …` and `would arm: …` instead of notifying and arming |
| `TD_TERMUX` | detected | `1` on Termux (its Python lives under `com.termux`), else `0`. Reminders (`tick`, `install`, `uninstall`, `fire`) need it; elsewhere they refuse and only the reminders are off |

## Failure modes

- **Reboot, or Termux force-stopped** — the alarm is gone until the next
  tick (open the agenda), which fires what came due meanwhile, late, and
  arms it again.
- **Termux put to sleep** — Android, and Samsung especially, can stop a
  sleeping app's alarms. Keep Termux and Termux:API unrestricted (see
  [Quick start](#quick-start)).
- **A failed arm** (helper missing, Android refused): logged in
  `~/.cache/td/alarm.log`, and the chain stops until the next tick
  arms it. `td tick` in a shell prints the error.
- **DST spring-forward (02:30 skipped)** — fires at 03:30, when the
  alarm's absolute time comes round.
- **DST fall-back (02:30 twice)** — `fired` makes it fire once.
- **A renamed bullet** — its task file becomes a file task or an orphan;
  rename the file to the new slug (or the bullet back) to relink.
- **`gf` on an orphan row** — the path is at the end of the line: press
  `gl` first, or use `space , p`.
- **No tap action** — `termux-open` needs the Termux:API app.

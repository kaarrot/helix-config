# agenda — `td` + `tl` design

Two companion scripts in this folder, both pure Python stdlib, both without
config files (env vars and defaults):

- `tl` — time log: clock in and out of task files, summaries
- `td` — todos: the inbox, task files, reminders, the agenda

Every key, and why each is built the way it is, is in [keys.md](keys.md).
This file is the design.

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

A long-lived task can live in its file alone, with no todo.md bullet: give
the file a status on its first line, `# [W] renew passport`. The agenda
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
or `- [ ] `) is a time-log entry: `td` never fires its leading time, and
`tl` logs it, or flags it under "Check by hand" if it is malformed. Any
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
- in `~/tasks/*.md`, on any line, while the file's todo.md bullet is open.
  A bullet marked done by hand, or with `space . x`, stops its file too,
  whatever the heading says. A file with no bullet fires unless its first
  heading is `# [x]`, `# [X]` or `# [!]`.

Except the leading time of a time-log entry (above).

### When it fires

`td tick` runs every 15 minutes. A reminder fires on the first tick at or
after its time minus the lead time, `TD_LEAD_MIN` (default 15). Ticks are
15 minutes apart, so it fires 0–15 minutes before it is due.

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
- A tick delayed by Doze or a reboot still fires what came due meanwhile,
  however late.

Each (file, time) fires once (`~/.cache/td/fired`). Editing the time makes
it a new reminder.

### How it runs

```
  file edit (helix)         Android JobScheduler (every 15m)
         │                           │
         ▼                           ▼
  ~/tasks/*.md ◀──────────── td-tick ──▶ td tick
                                           │
                     ┌─ scan + regex ──────┤
                     │                     │
                     ▼                     ▼
                scheduled           fired (dedup)
              (future gate)              │
                     │                   ▼
                     └────────▶ termux-notification + Nudge.wav
```

`td install` registers one periodic job with Android's JobScheduler:
`termux-job-scheduler --job-id 7421 --period-ms 900000 --persisted true`.
Android owns the timer, so the tick runs with Termux in the background, and
`--persisted` keeps the job across reboots. 15 minutes is Android's
minimum. The fixed job id means re-running `td install` replaces the job
rather than adding one.

The job runs `~/.config/helix/bin/td-tick`, a two-line shim that
`td install` writes:

```sh
#!/bin/sh
exec /data/data/com.termux/files/usr/bin/python3 /data/data/com.termux/files/home/.config/helix/bin/td tick
```

It holds no settings (the job doesn't see `.bashrc` exports): the defaults
live in `td`, so re-running `td install` changes nothing else.
`space , Enter` runs the same shim, so manual and scheduled ticks behave
alike. Check the job with `termux-job-scheduler --pending` (expect job
7421); remove it with `td uninstall`.

Each tick:

1. **Scans** `$TL_DIR/*.md`, plus `$TD_FILE` if it lives elsewhere, for the
   times that can fire (above).
2. **Records** each time not yet due (minus the lead) in `scheduled`.
3. **Fires** each time that is due (minus the lead), not yet in `fired`,
   and in `scheduled` or added since the previous tick, then adds it to
   `fired` and saves this tick's time in `last-tick`.

The notification is titled `TODO`. Its text is the bullet's text, or the
task file's first heading (its name if it has none). Tapping it opens the
file (needs the Termux:API app), and `~/dotemacs/Nudge.wav` plays if it
exists.

## The agenda

`space , a` writes `~/.cache/td/agenda.md` and opens it:

```
# td VIEW ONLY (status keys change the task itself; space , p goes there): [ ] todo  [Y] today  [A] active  [W] waiting

# TODAY

- [Y] pay rent

# ACTIVE

- [A] refactor td parser (*)

# TODO

- [ ] call jon

# WAITING

- [W] renew passport  ~/tasks/passport.md:1:1

# ORPHANS

- old-task  ~/tasks/old-task.md:1:1
```

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
`space , P` leave rows and tasks alone. `space , q` adds a new task at
the end of todo.md. For anything else, `space , p` to the task. How the keys manage this is in
[keys.md](keys.md#how-the-keys-are-built).

## Recurring tasks

A repeater after the stamp, `++Nu` or `.+Nu` (N ≥ 1, u = `d`|`w`|`m`|`y`),
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

Months clamp the day: Jan 31 + 1m → Feb 28/29; Feb 29 + 1y → Feb 28. The
repeater must be a word of its own: `C++1d` and `++1days` are text, and so
is `++0d` (it would never move), so those lines are just marked done.
`space . x` ignores repeaters.

## Commands

| command | does |
|---------|------|
| `td install` | write the `td-tick` shim, register job 7421 (every 15 min) |
| `td uninstall` | cancel the job, remove the shim |
| `td tick` | what the job runs: scan, record future times, fire due ones |
| `td list [--state todo\|today\|active\|waiting\|all] [--sort added\|modified]` | write the agenda to `~/.cache/td/agenda.md` and stdout, and the options to `~/.cache/td/agenda-args` |
| `td promote [--from PATH:LINE]` | stdin: a line. Create or reuse the bullet's task file (not from the agenda), then print where `space , P` goes and write it to `~/.cache/td/open` |
| `td jump [--from PATH:LINE]` | stdin: a line. Print where `space , p` goes and write it to `~/.cache/td/open` |
| `td toggle S [--from PATH [--line N]]` | toggle the line's state between `[ ]` and `S` (a name like `waiting` works too); stdin to stdout, or with `--line` the file on disk. On an agenda row, the task it shows changes instead, and the agenda is rebuilt. Keeps the task's other copies in step (see [keys.md](keys.md#status-keys-in-other-files)); moves a repeating date instead of marking done |
| `td set PATH LINE S` | set the checkbox at `PATH:LINE` to `S` |
| `td stamp [--restamp] [--col N]` | stdin: a line. Add a stamp, or move its date to today keeping the time; `--restamp`, or `--col N` on the stamp, only fixes the weekday |
| `td shift +N\|-N [--col N]` | stdin: a line. Move its stamp by the part under column N (the day without `--col`); with `--col`, save the part's new column to `~/.cache/td/stamp-col` |
| `td new [--state S]` | print `- [S] ` (`space , q` inserts it) |
| `td next` | print the next time due (for a status line) |
| `td fire PATH` | fire a file's notification now (testing) |
| `td test [-v]` | run the tests |

## Cache files

Under `~/.cache/td/`. The task files are the source of truth; these only
remember what `td` has seen. Reminders are keyed by (file, time), tasks by
(file, text without its stamp).

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

## Environment

| var | default | effect |
|-----|---------|--------|
| `TL_DIR` | `~/tasks` | the task folder |
| `TD_FILE` | `$TL_DIR/todo.md` | the inbox |
| `TD_LEAD_MIN` | `15` | fire this many minutes before the stamped time; 15 is one tick, so a reminder fires on the last tick before it is due. `0` fires 0–15 minutes after |
| `TL_NOW` | (unset) | fake clock, `YYYY-MM-DD HH:MM`, for tests |
| `TD_DRY_RUN` | (unset) | `1` prints `would fire: …` instead of notifying |

## Failure modes

- **Doze, airplane mode, reboot** — the tick runs late but fires everything
  that came due meanwhile. To keep delays short, set Termux to
  *unrestricted* in Android's battery settings.
- **DST spring-forward (02:30 skipped)** — fires on the next tick after
  03:00.
- **DST fall-back (02:30 twice)** — `fired` makes it fire once.
- **A renamed bullet** — its task file becomes a file task or an orphan;
  rename the file to the new slug (or the bullet back) to relink.
- **`gf` on an orphan row** — the path is at the end of the line: press
  `gl` first, or use `space , p`.
- **No tap action** — `termux-open` needs the Termux:API app.

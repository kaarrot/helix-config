# agenda — `td` + `tl` design & workflow

Two companion scripts in this folder, both pure Python stdlib, both config-less
(env vars + defaults, no TOML).

- `tl` — time-log helper (date-stamped bullets, "start / stop / out / summary")
- `td` — todo scheduler + agenda (this doc focuses on `td`)

## Two-tier task model

**Tier 1 — the inbox.** A single file `$TD_FILE` (default `~/tasks/todo.md`)
holds lightweight, fire-and-forget bullets:

```
- [ ] call jon
- [y] pay rent
- [a] refactor td parser
- [x] took bins out
- [!] call mom
```

Bullets stay clean — no inline link to the dedicated file. The agenda
renders `(*)` next to bullets whose slug has a dedicated file on disk, so
you can see at a glance which ones have notes. Press `space , p` on a
bullet to jump into that file; `space , P` creates it if it's missing.

The character inside the checkbox is the state:

| char  | meaning   |
|-------|-----------|
| `[ ]` | todo      |
| `[y]` | today     |
| `[a]` | active    |
| `[x]` | done      |
| `[!]` | ignore    |

Inbox bullets may carry an inline `YYYY-MM-DD HH:MM` timestamp — press
`space , s` to stamp the current line with "now", then edit. `[x]`/`[!]`
bullets never fire.

**Tier 2 — dedicated follow-up files.** One markdown file per task in `$TL_DIR`
(default `~/tasks`), created on promote. Notes + an optional timestamp:

```
# refactor td parser

2026-11-01 10:00

- outline the parser rewrite
- benchmark old vs new
```

Any `YYYY-MM-DD HH:MM` on any line fires a Termux notification at that
time — no `SCHEDULE:` marker needed. The one exception: timestamps
followed by ` - ` are ignored (that's `tl`'s running-entry shape,
`YYYY-MM-DD HH:MM - note`), so a task file's time log never fires.

### "First seen as future" rule

A timestamp fires only if `td tick` observed it in the future on a prior
tick (recorded in `~/.cache/td/scheduled`). Consequences:

- Random past-date mentions in notes never fire — they're already past
  on first observation, so they never enter `scheduled`.
- `tl` entries never fire (double-protected: the ` - ` lookahead keeps
  them out of the regex, and even if they slipped past, they're always
  past at write time).
- Doze-mode / reboot misses are still fired: the entry is already in
  `scheduled` from a prior tick, so the next tick after wake fires it.
- There is no `TD_CATCHUP_H` — a missed fire fires whenever `tick`
  next runs, regardless of how late. The sidecar is the whole story.

## Keybindings

Under `[keys.normal.space.","]` in `~/.config/helix/config.toml` (the `space ,`
namespace is reserved for `td`/`tl`; `space .` holds AI-tool launchers):

| key | action |
|-----|--------|
| `space , t` | open the inbox (`~/tasks/todo.md`) |
| `space , l` | agenda in a reusable buffer — grouped TODAY / ACTIVE / TODO, newest-added first |
| `space , L` | same agenda, sorted by file mtime |
| `space , P` | **create + jump**: promote current bullet to `~/tasks/<slug>.md` (reuses if exists), save the inbox, then jump into the file. Bullet text in the inbox is left unchanged |
| `space , p` | **jump**: open `~/tasks/<slug>.md` for the current bullet if it exists; otherwise no-op |
| `space , y` | toggle `[ ]` ↔ `[y]` (today); on an agenda row, mutates the source bullet in the inbox |
| `space , a` | toggle `[ ]` ↔ `[a]` (active); on an agenda row, mutates the source bullet in the inbox |
| `space , x` | toggle `[ ]` ↔ `[x]` (done). If the line carries a `++Nu`/`.+Nu` repeater (u = d\|w\|m\|y), **bumps the stamped date instead** and keeps `[ ]` — see [Recurring tasks](#recurring-tasks) |
| `space , s` | stamp the current line with `YYYY-MM-DD Xxx HH:MM` (now, weekday included). If a stamp already exists, replace its date with today's and keep the time. Inbox bullets with such a stamp fire a notification |
| `space , R` | restamp — recompute **only the weekday** on the current line to match its date (useful after manually editing the date part) |
| `space , <ret>` | fire a tick manually (`:write` + `td-tick`); same code the 15-min scheduler runs. Useful for testing without waiting |
| `space . x` | plain `[ ]` ↔ `[X]` sed toggle (predates `td`, no repeater handling; works in any file) |

`space , p` works both in the inbox (slugify current bullet) and in the
agenda buffer (slugify the bullet text, trailing ` (*)` marker stripped).
Orphan rows carry a `path:line:col`, so `space , p` on an orphan jumps
straight to that file.

### Why `P` and `p` are separate

Bullets no longer carry a ` → <path>` suffix, so jumping must resolve
`bullet text → ~/tasks/<slug>.md` by slugifying on the fly. If the same
key both jumped and created-on-miss, every typo would silently spawn an
orphan file (`refacror td parser` → `refacror-td-parser.md`). Splitting
them makes:

- `p` **read-only** — jump if the file exists, no-op otherwise. Safe to
  mash on anything.
- `P` **explicit write** — the verb that creates the dedicated file.
  Uppercase matches the Vim convention that capital = more deliberate.
  `P` also jumps into the newly-created file as a convenience; the key
  distinction is that `P` *can create*, `p` *never does*.

## Agenda row format

Bullet rows have no path — just the checkbox, text, and a trailing ` (*)` if a
dedicated file exists for that slug. Orphan rows carry a `path:line:col` so
`gf` (or `space , p`) jumps straight to the file:

```
# td: [ ] todo  [y] today  [a] active

# TODAY

- [y] pay rent

# ACTIVE

- [a] refactor td parser (*)

# TODO

- [ ] call jon

# ORPHANS

- old-task  ~/tasks/old-task.md:1:1
```

The `# ORPHANS` section lists dedicated files in `$TL_DIR` with no matching
inbox bullet — files you've either forgotten about or deleted the bullet for.

### Why bullet rows have no path

Paths used to trail every bullet (`~/tasks/todo.md:N:1`) so `gf` could jump to
the inbox line and `td toggle` could propagate state changes to disk. Both
jobs are now covered differently:

- Jumping to the dedicated file goes through `space , p`, which slugifies the
  current line — no path needed.
- `td toggle` takes `--from PATH`: when PATH isn't `$TD_FILE`, it text-matches
  the bullet in the inbox and flips the first exact match on disk.

The trade-off: identical bullet text in `$TD_FILE` means only the first match
gets toggled — a nearly-never scenario, and visible in the agenda itself.
When this happens, `td toggle` emits a warning to stderr naming the duplicate.

### Why `P`/`y`/`a` don't use `:pipe`

The Helix bindings `:write` the current buffer and then invoke `td` with
`--from PATH --line N`. `td` reads the line from disk, writes the toggled
or promoted version back to disk, and refreshes `agenda.md`. `auto-reload`
picks up the change — the editor buffer stays clean (no `:pipe`-dirty races).

## Recurring tasks

An org-style repeater token `++Nu` or `.+Nu` (u = `d`|`w`|`m`|`y`) after
the stamp turns a bullet into a recurring one. Pressing `space , x` on
such a line bumps the stamped date instead of marking done; state stays
`[ ]`. The repeater and surrounding text are preserved.

```
- [ ] pay rent 2026-10-01 Thu 09:00 ++1m        # → 2026-11-01 Sun 09:00 after `space , x`
- [ ] water plants 2026-09-15 Tue 07:30 .+2w    # → today+2w, time preserved
- [ ] standup 2026-10-10 Sat 09:00 ++1w         # weekly on the same hour
```

| prefix | semantics |
|--------|-----------|
| `++Nu` | **anchored**: new = old_date + N units, repeated until `>today`. Missed cycles don't pile up; "rent on the 1st" stays on the 1st even if you tick late. |
| `.+Nu` | **floating**: new = today + N units (time-of-day preserved from the stamp). "Water plants ~2w from when I remembered." |

Month arithmetic clamps the day: Jan 31 + 1m → Feb 28/29. Feb 29 + 1y →
Feb 28. Comparison uses the full `datetime` (date + time), so `++1m` on
a stamp that already lies in the future still advances by one step.

Plain `space . x` (the sed-based toggle) ignores repeaters and just
flips `[ ]` ↔ `[X]` — useful for one-off `[X]` in any file.

## Architecture — how a reminder actually fires

End-to-end there are four moving parts: the OS clock, a shim, the
scanner, and the two sidecars. Each is tiny; the design keeps state in
the files you edit.

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

### 1. The clock — Android's JobScheduler

`td install` registers one periodic job:
`termux-job-scheduler --job-id 7421 --period-ms 900000 --persisted true`.
Android (not Termux) owns the timer, so the tick fires even when Termux
is backgrounded; `--persisted` keeps it across reboot. 15 min is the OS
minimum. Doze mode can delay a tick but doesn't drop it — the next tick
after wake fires anything that came due in between.

### 2. The shim — `~/.config/helix/bin/td-tick`

Three lines of sh that the JobScheduler invokes. Its only job: set
`TD_LEAD_MIN` and `exec python3 td tick`. Kept separate from `td` so you
can edit the exported env without touching the Python. The same shim is
wired to `space , <ret>` in Helix, so manual and scheduled ticks share
the same code path and env.

### 3. The tick — `td tick`

Each run does three things:

1. **Scan.** Walk `$TL_DIR/*.md` + `*.txt`. For each line, find
   `YYYY-MM-DD [Xxx] HH:MM` **not** followed by ` - ` (the lookahead
   excludes `tl` running-entry logs).
2. **Gate.** For each match, compute `(path, due_iso)` hash. If
   `due_iso > now` and the hash isn't in `scheduled`, record it. If
   `due_iso ≤ now` and the hash isn't in `scheduled`, **drop it** — the
   stamp was first observed in the past, so it's a note, not a reminder.
   This is the "first seen as future" rule.
3. **Fire.** For each hash in `scheduled` where
   `due − TD_LEAD_MIN ≤ now` and the hash isn't in `fired`, invoke
   `termux-notification` + `termux-media-player`, then append to `fired`.

The gate is why random past dates in notes never fire. The dedup is why
Doze catch-up or DST fall-back can't double-fire a reminder.

### 4. Authoring from Helix

Stamps live in the files you edit; there is no separate schedule store.

- `space , s` → `td stamp` inserts/replaces a `YYYY-MM-DD Xxx HH:MM`.
- `space , R` → `td stamp --restamp` fixes only the weekday after you
  hand-edit the date.
- `space , x` → `td toggle x`: on a line with a `++Nu`/`.+Nu` repeater,
  bump the stamp (new hash → new row in `scheduled` → re-arms as a new
  reminder); otherwise mark `[x]`.
- `space , <ret>` → fire a tick now (same shim the OS runs).

Delete the line, no more reminder. Edit the time, old hash falls out and
a new one arms. The sidecars are fast caches of what the files already
say — the files are source of truth.

## Firing mechanism

`td install` registers one periodic `termux-job-scheduler` job (job-id 7421,
every 15 min — the Android minimum, `--persisted true` so it survives reboot).
Android's `JobScheduler` calls the shim at `~/.config/helix/bin/td-tick`,
which runs `td tick`. `td tick` scans every `~/tasks/*.md` file (including
the inbox) for `YYYY-MM-DD HH:MM` timestamps. The "first seen as future"
rule above decides what fires.

Verify with `termux-job-scheduler --pending` (expect job 7421). Uninstall
with `td uninstall`. For on-demand testing without waiting 15 min, press
`space , <ret>` or run `td tick` in a shell. Doze mode can delay the
scheduler but never drops fires — the `scheduled` sidecar persists across
sleep/reboot.

Dedup via `~/.cache/td/fired` — hash of `(path, due_iso)`. Edit the
timestamp → new iso → re-arms as a new reminder.

Notification shape:

```
termux-notification --title "TODO" --content "<file title>" --sound \
    --action "termux-open <file>"
termux-media-player play ~/dotemacs/Nudge.wav   # if present
```

Title = first `# H1` in the file, or the filename stem.

## Commands

| command | behavior |
|---------|----------|
| `td install` | write the shim at `~/.config/helix/bin/td-tick`, register job-id 7421 |
| `td uninstall` | cancel the job, remove the shim |
| `td tick` | what the job calls — scan every `~/tasks/*.md`, fire due timestamps |
| `td list [--state S] [--sort added\|modified]` | write the agenda to `~/.cache/td/agenda.md` and stdout; marks `(*)` for bullets with a dedicated file; lists `# ORPHANS` |
| `td promote [--from PATH --line N]` | create/reuse `~/tasks/<slug>.md` for a bullet. With `--from/--line` reads the file (no stdout); otherwise reads stdin and echoes |
| `td jump --from PATH:LINE` | print `~/tasks/<slug>.md` if the bullet at `PATH:LINE` has a dedicated file; else print `PATH` (no-op fallback) |
| `td set PATH LINE S` | rewrite the checkbox char at `PATH:LINE` to `S` |
| `td toggle S [--from PATH [--line N]]` | toggle the bullet's state. With `--from/--line` reads the file and writes back (no stdout); otherwise reads stdin and echoes. Propagates to `$TD_FILE` when source differs |
| `td new [--state S]` | print `- [S] ` template for pipe/insert |
| `td stamp [--restamp]` | stdin: a line. Insert/replace a `YYYY-MM-DD Xxx HH:MM` stamp (today's date, keeps the time if one exists). `--restamp` only fixes the weekday to match the date. `tl` log entries are left alone and a fresh stamp is appended |
| `td next` | print the next-due timestamp (for a statusline) |
| `td fire PATH` | fire a file's timestamp now (testing) |
| `td test [-v]` | run the embedded unittest suite |

## Slug rules (used by `td promote`)

Full slug with dashes — lowercase, strip punctuation, collapse runs:

- `Costco run!` → `costco-run.md`
- `costCo RUN` → `costco-run.md` (same)
- `refactor TD parser` → `refactor-td-parser.md`

If a file with that slug already exists, it is **reused** (not overwritten,
not appended with `_2`). This is deliberate: `costCo RUN` and `Costco run!`
link back to the same file.

## Sidecars

Under `~/.cache/td/`:

- `fired` — append-only dedup log, `due_iso \t hash \t short_text`. One row per
  fired notification; `(hash, due_iso)` keyed, so editing the time re-arms.
- `scheduled` — append-only first-seen-as-future log,
  `first_seen_iso \t hash \t due_iso \t short_text`. The "first seen as
  future" gate: only entries whose `(hash, due_iso)` lives here are
  eligible to fire. Random past-date mentions in notes never land here.
- `added` — append-only first-seen log, `first_seen_iso \t hash \t short_text`.
  Used for "newest-added first" sort order.
- `agenda.md` — the reusable agenda buffer, overwritten by every `td list`.

## env vars

| var             | default                   | effect |
|-----------------|---------------------------|--------|
| `TL_DIR`        | `~/tasks`                 | folder scanned for dedicated files |
| `TD_FILE`       | `$TL_DIR/todo.md`         | the inbox file scanned by `td list` |
| `TL_NOW`        | (unset)                   | fake wall-clock, `YYYY-MM-DD HH:MM`; used by tests |
| `TD_LEAD_MIN`   | `0`                       | fire this many minutes earlier than the stamped time |
| `TD_DRY_RUN`    | (unset)                   | `=1` prints `would fire: …` instead of sending a notification |

### Why set `TD_LEAD_MIN=15`

Android caps `termux-job-scheduler` periodic jobs at a 15-min minimum.
With `TD_LEAD_MIN=0` (default), a stamp fires on the first tick where
`now ≥ due` — which can land **0–15 min after** the stamped time. Set
`TD_LEAD_MIN=15` to shift the fire window one full tick period earlier:
items then fire 0–15 min **before** due (same model as emacs
`appt-message-warning-time`). Caveat: stamping something less than 15
min in the future with lead=15 means `fire_at` is already past when
first observed → the first-seen-as-future gate rejects it. Stamp
≥15 min ahead for lead-time mode to work.

Set it in the shim so both the scheduler job and manual `space , <ret>`
ticks see the same value (shell `.bashrc` exports don't reach the job):

```sh
# ~/.config/helix/bin/td-tick
#!/bin/sh
export TD_LEAD_MIN=15
exec /data/data/com.termux/files/usr/bin/python3 \
    /data/data/com.termux/files/home/.config/helix/bin/td tick
```

Note: re-running `td install` overwrites the shim and drops the export.

## Quick reference

- shim:   `~/.config/helix/bin/td-tick` (written by `td install`)
- job id: `7421` (termux-job-scheduler)
- tests:  `~/.config/helix/bin/td test`

## Failure modes

- **Doze mode / airplane / reboot** — the `scheduled` sidecar persists
  future entries; the next tick after wake fires anything whose due has
  passed, no matter how late.
- **DST spring-forward (02:30 skipped)** — that wall-clock never happens; fires
  on the next tick after 03:00.
- **DST fall-back (02:30 twice)** — hash dedup fires it once.
- **File edited mid-tick** — `fired` hashes `(path, due_iso)`; changing the
  time → new hash → re-arms (and the new time must again be observed in
  the future before it can fire).
- **Duplicate job on reinstall** — fixed `--job-id 7421`; `td install` cancels
  first.
- **Clock skew for tests** — honor `TL_NOW` (same env var `tl` uses).
- **`gf` on agenda row** — path sits at end-of-line; press `gl` (goto end)
  first, then `gf`.
- **No notification tap-action** — `--action "termux-open <file>"` needs the
  Termux:API addon.

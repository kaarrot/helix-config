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
you can see at a glance which ones have notes. Press `space . p` on a
bullet to jump into that file; `space . P` creates it if it's missing.

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
| `space , s` | stamp the current line with `YYYY-MM-DD HH:MM` (now). Same-line, no trailing dash — inbox bullets with such a stamp fire a notification |
| `space . x` | toggle `[ ]` ↔ `[X]` (lives in `space .` — predates `td`; works in any file) |

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
`gf` (or `space . p`) jumps straight to the file:

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

- Jumping to the dedicated file goes through `space . p`, which slugifies the
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

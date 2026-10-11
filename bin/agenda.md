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

No inline timestamps on inbox bullets — scheduling lives in dedicated files.

**Tier 2 — dedicated follow-up files.** One markdown file per task in `$TL_DIR`
(default `~/tasks`), created on promote. Notes + an optional `SCHEDULE` line:

```
# refactor td parser

SCHEDULE: 2026-11-01 10:00

- outline the parser rewrite
- benchmark old vs new
```

The `SCHEDULE` line triggers a Termux notification at that time. Format is
flexible — any line containing both the word `SCHEDULE` and a
`YYYY-MM-DD HH:MM` timestamp counts. Recommended form `SCHEDULE: <date>`
(SCHEDULE first) so it doesn't collide with `tl`'s `YYYY-MM-DD HH:MM - …`
running-entry shape.

## Keybindings

Under `[keys.normal.space."."]` in `~/.config/helix/config.toml`:

| key | action |
|-----|--------|
| `space . t` | open the inbox (`~/tasks/todo.md`) |
| `space . l` | agenda in a reusable buffer — grouped ACTIVE / TODAY / TODO, newest-added first |
| `space . L` | same agenda, sorted by file mtime |
| `space . P` | **create + jump**: promote current bullet to `~/tasks/<slug>.md` (reuses if exists), save the inbox, then jump into the file. Bullet text in the inbox is left unchanged |
| `space . p` | **jump**: open `~/tasks/<slug>.md` for the current bullet if it exists; otherwise no-op |
| `space . y` | toggle `[ ]` ↔ `[y]`; on an agenda row, mutates the source bullet |
| `space . x` | toggle `[ ]` ↔ `[X]` (predates `td`; works in any file) |

`space . p` works both in the inbox (slugify current bullet) and in the
agenda buffer (slugify the bullet text to the left of the trailing
`path:line:col`). In the agenda, pressing `goto_line_end` (`gl`) then `gf`
still works as a path-based alternative.

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

# ACTIVE

- [a] refactor td parser (*)

# TODAY

- [y] pay rent

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

## Firing mechanism

`td install` registers one periodic `termux-job-scheduler` job (every 15 min —
the Android minimum, `--persisted true` so it survives reboot). The job runs
`td tick`, which scans all `~/tasks/*.md` files (inbox excluded) for `SCHEDULE`
lines and fires any whose timestamp is due within the last `TD_CATCHUP_H`
hours (default 6).

Dedup via `~/.cache/td/fired` — hash of `(path, due_iso)`. Edit the SCHEDULE
line → new iso → re-arms as a new reminder.

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
| `td tick` | what the job calls — scan dedicated files, fire due SCHEDULEs |
| `td list [--state S] [--sort added\|modified]` | write the agenda to `~/.cache/td/last-list.md` and stdout; marks `(*)` for bullets with a dedicated file; lists `# ORPHANS` |
| `td promote` | stdin: a bullet. Creates/reuses `~/tasks/<slug>.md`; echoes bullet unchanged |
| `td jump --from PATH:LINE` | print `~/tasks/<slug>.md` if the bullet at `PATH:LINE` has a dedicated file; else print `PATH` (no-op fallback) |
| `td set PATH LINE S` | rewrite the checkbox char at `PATH:LINE` to `S` |
| `td toggle S` | stdin: a line. If it's an agenda row, update the source via `set`. Else toggle in place |
| `td new [--state S]` | print `- [S] ` template for pipe/insert |
| `td next` | print the next-due SCHEDULE (for a statusline) |
| `td fire PATH` | fire a dedicated file's SCHEDULE now (testing) |
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

- `fired` — append-only dedup log, `due_iso \t hash \t short_text`. Pruned to
  2× `TD_CATCHUP_H` on each tick.
- `added` — append-only first-seen log, `first_seen_iso \t hash \t short_text`.
  Used for "newest-added first" sort order. Hashes strip the ` → <path>`
  suffix so promoting doesn't bump the task to the top.
- `last-list.md` — the reusable agenda buffer, overwritten by every `td list`.

## env vars

| var             | default                   | effect |
|-----------------|---------------------------|--------|
| `TL_DIR`        | `~/tasks`                 | folder scanned for dedicated files |
| `TD_FILE`       | `$TL_DIR/todo.md`         | the inbox file scanned by `td list` |
| `TL_NOW`        | (unset)                   | fake wall-clock, `YYYY-MM-DD HH:MM`; used by tests |
| `TD_CATCHUP_H`  | `6`                       | hours of catchup window on each tick |
| `TD_LEAD_MIN`   | `0`                       | fire this many minutes earlier than the stamped time |
| `TD_DRY_RUN`    | (unset)                   | `=1` prints `would fire: …` instead of sending a notification |

## Quick reference

- shim:   `~/.config/helix/bin/td-tick` (written by `td install`)
- job id: `7421` (termux-job-scheduler)
- tests:  `~/.config/helix/bin/td test`

## Failure modes

- **Doze mode / airplane / reboot** — catchup window (default 6 h) catches
  reminders missed while the job couldn't run.
- **DST spring-forward (02:30 skipped)** — that wall-clock never happens; fires
  on the next tick after 03:00, within catchup.
- **DST fall-back (02:30 twice)** — hash dedup fires it once.
- **File edited mid-tick** — `fired` hashes the SCHEDULE line's `(path, due)`;
  changing the time → new hash → re-arms.
- **Duplicate job on reinstall** — fixed `--job-id 7421`; `td install` cancels
  first.
- **Clock skew for tests** — honor `TL_NOW` (same env var `tl` uses).
- **`gf` on agenda row** — path sits at end-of-line; press `gl` (goto end)
  first, then `gf`.
- **No notification tap-action** — `--action "termux-open <file>"` needs the
  Termux:API addon.

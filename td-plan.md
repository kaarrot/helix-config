# TODO Scheduler — `td`

## Context

You want two complementary things in one tool:

1. **Timed reminders** — any line carrying a plain `YYYY-MM-DD HH:MM` stamp fires a Termux notification at that time, reliably, regardless of what's running. No `SCHEDULE:` marker needed; the timestamp alone is the signal. Works in both inbox bullets and dedicated task files.
2. **Long-running backlog with lightweight state** — state lives inside the checkbox character: `[ ]` todo, `[y]` today, `[a]` active, `[x]` done, `[!]` ignore. One file (`$TD_FILE`, default `~/tasks/todo.md`) holds the inbox; promoting a bullet creates a dedicated `~/tasks/<slug>.md` for notes.

The design mirrors `~/.config/helix/bin/tl`: pure Python stdlib, plain-text data in `$TL_DIR`, env-var config, no deps.

## Approach

1. Two-tier task model. Inbox bullets live in `$TD_FILE` (`~/tasks/todo.md`). Dedicated files live alongside in `$TL_DIR` (`~/tasks/*.md`), one per promoted task. State is in the checkbox char (`[ ]`/`[y]`/`[a]`/`[x]`/`[!]`); timestamps are plain `YYYY-MM-DD HH:MM` anywhere in any `~/tasks/*.md` file.
2. Register **one** periodic `termux-job-scheduler` job (every 15 min, the Android minimum, `--persisted true`). The job runs `td tick`, which scans every `~/tasks/*.md` (inbox + dedicated) for `YYYY-MM-DD HH:MM` stamps and fires any that are due.
3. **First-seen-as-future gate.** A timestamp fires only if `td tick` previously observed it in the future. Future-observed stamps are recorded in `~/.cache/td/scheduled`. Consequence: random past-date mentions in notes never fire; `tl` log entries (shape `YYYY-MM-DD HH:MM - note`) never fire (double-protected: the regex has a `(?! - )` lookahead, and even if it slipped past, it's past at write time).
4. Dedup fired reminders in `~/.cache/td/fired`, keyed on `(path, due_iso)` hash. Editing the time → new hash → re-arms as a new reminder. Track task first-seen time in `~/.cache/td/added` so "sort by recently added" works even though markdown has no creation stamp.
5. `td list` writes a grouped TODAY / ACTIVE / TODO view to `~/.cache/td/agenda.md` plus stdout. Open that file once in Helix — `auto-reload = true` refreshes it in place on each re-run. One reusable buffer, not a stream of popups.
6. No new config file. Reuse `TL_DIR` env var; add `TD_LEAD_MIN` only (default 0).

## Line format

**Inbox bullets** (`$TD_FILE`, default `~/tasks/todo.md`) — state in the checkbox, timestamp inline (same line, no trailing dash):

```
- [ ] call jon                              # plain backlog, no fire
- [a] refactor td parser                    # active
- [y] pay rent 2026-10-10 18:30             # today + timed
- [ ] test ping 2026-10-10 11:35            # timed, no state
- [x] took bins out                         # done — never fires
- [!] call mom                              # ignored — never fires
```

**Dedicated files** (`$TL_DIR/<slug>.md`, created by `td promote`) — any `YYYY-MM-DD HH:MM` on any line fires:

```
# refactor td parser

2026-11-01 10:00

- outline the parser rewrite
- benchmark old vs new
```

Parsing rules (match `tl`'s tolerant style — unparseable lines pass through untouched):

- Inbox candidate iff `^\s*- \[[ yaxX!]\]\s+` matches.
- Timestamp regex: `(\d{4}-\d{2}-\d{2}) (\d{1,2}:\d{2})(?! - )` — the negative lookahead excludes `tl`'s `YYYY-MM-DD HH:MM - note` entry shape, so a task file's time log never fires.
- Fire eligibility: inbox lines must be `[ ]`/`[y]`/`[a]` (not `[x]`/`[!]`); dedicated-file lines fire from any line (except `tl`-shaped). Both are gated by the first-seen-as-future rule.

Coexistence with `tl`: the `(?! - )` lookahead keeps `tl` entries out of the match; even if one slipped past, it's past at write time, so the first-seen-as-future gate rejects it.

Your existing `space . x` keybinding (sed-toggle `[ ]`↔`[X]`) still works for marking done — no change.

## Sidecars

### `~/.cache/td/scheduled` — first-seen-as-future gate

Append-only, TAB-separated: `first_seen_iso \t sha1(path, due_iso) \t due_iso \t short_text`. Each `td tick` iteration, every `(path, due_iso)` observed in the future gets a row here if it isn't already recorded. Firing is gated on membership: a timestamp fires only if its `(hash, due_iso)` lives here.

Why this exists: random past-date mentions in notes should never fire, and `tl` log entries should never fire. Both are naturally past at first observation, so they never enter `scheduled`. Doze-mode / reboot misses still fire, because the entry was recorded on a prior tick and survives the gap.

### `~/.cache/td/fired` — fired-reminder dedup

Append-only, TAB-separated: `due_iso \t sha1(path, due_iso) \t short_text`. Prevents re-firing the same `(path, due)` twice. Editing the time → new hash → re-arms (and the new stamp must again be observed in the future to be eligible).

### `~/.cache/td/added` — first-seen timestamp per task

Append-only, TAB-separated: `first_seen_iso \t sha1(same as above) \t short_text`. Populated by `td tick` and `td list` the first time a new hash appears. Needed because markdown has no creation stamp — without this, "sort by recently added" would be impossible.

### `~/.cache/td/agenda.md` — reusable listing buffer

Overwritten by every `td list` call. Open once in Helix (`:open <path>`), re-runs refresh in place thanks to `auto-reload = true`.

## Firing mechanism

Android's `JobScheduler` (via `termux-job-scheduler`) runs `td tick` periodically with no need for Termux to be open or the screen on.

**Install once:**

```bash
~/.config/helix/bin/td install
```

This writes a two-line shim and registers the job:

```
# ~/.config/helix/bin/td-tick (shim, written by `td install`)
#!/bin/sh
exec /data/data/com.termux/files/usr/bin/python3 \
    /data/data/com.termux/files/home/.config/helix/bin/td tick

# Job registration (equivalent command)
termux-job-scheduler \
    --job-id 7421 \
    --script ~/.config/helix/bin/td-tick \
    --period-ms 900000 \
    --persisted true
```

- `--period-ms 900000` → every 15 min (Android's minimum granularity).
- `--persisted true` → survives reboot.
- `--job-id 7421` → fixed id so re-running `td install` replaces (never duplicates) the entry.

**Verify:**

```bash
termux-job-scheduler --pending   # expect: Pending Job 7421: …/td-tick …
```

**Uninstall:**

```bash
~/.config/helix/bin/td uninstall   # cancels job 7421, removes the shim
```

**Manual tick** (for testing or on-demand refresh without waiting up to 15 min): `space , <ret>` in Helix, or `~/.config/helix/bin/td tick` in a shell.

**Doze mode caveat:** when the phone is idle/screen-off for a while, Android batches `JobScheduler` jobs — the 15-min cadence can slip to minutes or hours. The `scheduled` sidecar guarantees no fires are lost: whatever is due is fired on the next tick after wake. To minimise delay, set Termux to **unrestricted** in Android's battery settings.

**Per-tick logic.** For each timestamp observed in any `~/tasks/*.md`:

1. If `due > now`: record in `scheduled` if not already there, then skip.
2. If `due ≤ now`: skip unless `(hash, due_iso) ∈ scheduled` (gate), skip if already in `fired`, otherwise fire the notification and append to `fired`.

No catchup window — the `scheduled` sidecar is the whole story. A missed fire (Doze, airplane, reboot) fires on the next tick after wake, however late. The entry's hash is already in `scheduled` from a prior tick, so lateness doesn't matter.

**Lead time:** `TD_LEAD_MIN` (default 0) shifts the fire time earlier — e.g. `TD_LEAD_MIN=15` fires 15 min before the stamped time, matching your Emacs `appt-message-warning-time`.

**Notification shape** — reuse your existing style:

```
termux-notification --title "TODO" --content "<task text>" --sound \
    --action "termux-open <file>"
termux-media-player play ~/dotemacs/Nudge.wav   # only if the file exists
```

Tapping the notification opens the task file in your default viewer.

## Listing: `td list` → reusable buffer

Output format is grep-compatible so Helix's `gf` jumps to source:

```
# ACTIVE
/data/.../tasks/day.md:5: refactor td parser #active
/data/.../tasks/work.md:12: overhaul tests <2026-11-01 10:00> #active

# TODAY
/data/.../tasks/day.md:7: pay rent <2026-10-10 18:30> #today

# TODO
/data/.../tasks/day.md:3: call jon
/data/.../tasks/other.md:12: buy chili seeds #errand
```

Within each state group, sort order is controlled by `--sort`:

- `--sort added` (default) — first-seen ISO from `~/.cache/td/added`, newest first (highest at top).
- `--sort modified` — file mtime, newest first.

Filters:

- `--state active | today | todo | all` — default `all`. State headings suppressed when a single state is selected.
- `--tag T` — future, filter by any `#tag`. Reserved; CLI accepts it today, no-op for now.

Both `--sort` and `--state` can be combined. Output is **always** written to `~/.cache/td/last-list.md` *and* stdout, so the same command drives both the reusable buffer and shell pipelines.

### The reusable-buffer pattern

Open the listing file once as a real Helix buffer:

```
:open /data/data/com.termux/files/home/.cache/td/last-list.md
```

Because your `config.toml:24` has `auto-reload = true`, re-running `td list` from any keybinding refreshes the open buffer without closing/re-opening it. Put the cursor on a `path:line:` entry and press `gf` — Helix opens the task file at that line.

## Script layout: `~/.config/helix/bin/td`

Python 3 stdlib only (Termux ships 3.14; `tomllib` available if ever needed). Subcommands, mirroring `tl`'s pattern:

| Command | Behavior |
|---|---|
| `td install` | Write `~/.config/helix/bin/td-tick` shim, register the 15-min job. Idempotent (cancels prior job-id first). |
| `td uninstall` | `termux-job-scheduler --cancel 7421`, remove the shim. |
| `td tick` | What the job calls. Scan every `~/tasks/*.md` for `YYYY-MM-DD HH:MM` stamps; record future-observed ones in `scheduled`; fire anything whose `(hash, due_iso) ∈ scheduled ∧ due ≤ now ∧ hash ∉ fired`. |
| `td list [--state S] [--sort added\|modified]` | Write grouped TODAY / ACTIVE / TODO agenda to `~/.cache/td/agenda.md` and stdout; mark `(*)` for bullets with a dedicated file; list `# ORPHANS` for dedicated files with no inbox bullet. |
| `td promote [--from PATH --line N]` | Create/reuse `~/tasks/<slug>.md` for the current bullet. |
| `td jump --from PATH:LINE` | Print `~/tasks/<slug>.md` if the bullet has a dedicated file; else print `PATH`. |
| `td toggle S [--from PATH [--line N]]` | Flip the checkbox char; propagates to `$TD_FILE` when invoked from agenda rows. |
| `td next` | Print the next-due timestamp (for statusline / one-off checks). |
| `td new [--state S]` | Print `- [S] ` prefix for pipe/insert. |
| `td fire PATH` | Fire a file's timestamp now (testing). |
| `td test [-v]` | Built-in unittest, mirrors `tl test`. |

Shared helpers borrowed from `tl` (same code shape, not imported — keep each script standalone like `tl` is):

- `TL_DIR` resolution (env, default `~/tasks`)
- `TL_NOW` support for clock faking in tests
- UTF-8 reads with `errors="surrogateescape"`
- Markdown file discovery via `folder.glob("*.md")` + `*.txt`

## Helix integration

Extend `[keys.normal.space."."]` in `~/.config/helix/config.toml`:

```toml
# TODO scheduler — ~/.config/helix/bin/td, same TL_DIR as tl
# Insert "- [ ] <now+1h> " template at cursor; type task + tags, save.
t = ":insert-output ~/.config/helix/bin/td new"
# Open the reusable listing buffer, sorted by recently added (default).
# Re-running refreshes the same buffer (auto-reload = true).
l = [":sh ~/.config/helix/bin/td list", ":open /data/data/com.termux/files/home/.cache/td/last-list.md"]
# Same, but sort by recently modified.
L = [":sh ~/.config/helix/bin/td list --sort modified", ":open /data/data/com.termux/files/home/.cache/td/last-list.md"]
```

Chosen letters don't collide with existing bindings (`i o r S x . m b v V c C g G a A d`). Narrower-state views (`#today` only, `#active` only) can be added later as `y` / `a`-chord bindings, or just run `:sh ~/.config/helix/bin/td list --state active` manually and the open buffer refreshes.

Workflow:

1. `space . t` → inserts `- [ ] <2026-10-10 11:30> ` template; you type the task text (and optionally `#active` or `#today`).
2. `space . l` → opens the reusable list, grouped Active / Today / Todo, newest-added at the top of each group.
3. Cursor on any `path:line:` row → `gf` → jump to that task's source line.
4. Edit → save → `space . l` again → list refreshes in the same buffer.

## Future hooks (not implemented now, design accommodates)

- **Tag filter:** `td list --tag errand` is reserved in the CLI; implementation is a one-line filter.
- **Custom picker:** `td list` output format is already grep-compatible; if you later install `fzf`, pipe `td list` through it before writing to the buffer file.
- **More states:** adding `#waiting`, `#maybe`, etc. is just adding entries to the `known_states` tuple in the script.
- **Config file:** if knobs multiply, add `~/.config/td.toml` and parse with stdlib `tomllib`. Not needed today.

## Critical files

- `/data/data/com.termux/files/home/.config/helix/bin/td` — new script
- `/data/data/com.termux/files/home/.config/helix/bin/td-tick` — new shim (written by `td install`)
- `/data/data/com.termux/files/home/.config/helix/config.toml` — add 3 keybindings under `[keys.normal.space."."]`
- `/data/data/com.termux/files/home/.cache/td/{fired,added,last-list.md}` — runtime state (created on first use)

## Reference files (read-only, for conventions)

- `/data/data/com.termux/files/home/.config/helix/bin/tl` — style, `TL_DIR` handling, `TL_NOW`, markdown parsing, test harness
- `/data/data/com.termux/files/home/dotemacs/emacs:1907-1941` — notification invocation pattern to mirror
- `/data/data/com.termux/files/home/tasks/day.md` — real-world mixed-content task file
- `/data/data/com.termux/files/home/.config/helix/config.toml:24` — the `auto-reload = true` the reusable buffer relies on

## Failure modes & mitigations

- **Doze mode / airplane / reboot** → the `scheduled` sidecar persists future entries; the next tick after wake fires anything whose due has passed, however late. `--persisted true` survives reboot.
- **File edited mid-tick** → `fired` hashes `(path, due_iso)`; changing the time → new hash → re-arms (and the new stamp must again be observed in the future to be eligible).
- **Random past-date mention in notes** → never fires. Past at first observation → never enters `scheduled` → gate rejects it forever.
- **`tl` log entries never fire** → double-protected: regex `(?! - )` lookahead keeps them out of the match; even if slipped past, they're past at write time, so gate rejects.
- **Duplicate job on reinstall** → fixed `--job-id 7421`; `td install` cancels first.
- **DST spring-forward** at 02:30 → that wall-clock never happens; fires on the next tick after 03:00.
- **DST fall-back** at 02:30 → wall-clock happens twice; `fired` hash dedup fires it once.
- **Clock skew for tests** → honor `TL_NOW` (same env var `tl` uses), same format.
- **"Added" sort empty on first run** → `added` sidecar is empty until first `td tick` or `td list` scans the files. First scan assigns `first_seen = min(file_mtime, now)` to seed the order; subsequent new tasks get `now`.
- **Edited task jumps to top of "added" list** → by design (hash changed = new task). Flagged here so you don't call it a bug.
- **Reusable buffer not refreshing** → Helix only auto-reloads if the buffer has no unsaved changes; make sure the list buffer stays unmodified (read-only in practice). If a stale buffer sticks, `:reload`.
- **`gf` can't resolve `path:line:`** → Helix supports `path:line:col:` for grep output. If the row format is just `path:line:text`, confirm `gf` jumps correctly; if not, change the row to `path:line:1:text`.
- **No notification tap-action** → `--action "termux-open <file>"` requires Termux:API; if absent, notification still shows, just no tap behavior.

## Verification

End-to-end test, done manually after implementation:

```bash
# 1. Install
~/.config/helix/bin/td install
termux-job-scheduler --pending   # expect job-id 7421 listed

# 2. Add tasks of each shape, by hand or via `space . t`:
cat >> ~/tasks/day.md <<'EOF'
- [ ] call jon
- [ ] #active refactor td parser
- [ ] #today pay rent <2026-10-10 18:30>
- [ ] test ping <2026-10-10 11:35>
EOF

# 3. Dry-fire the scheduler
~/.config/helix/bin/td tick
# → notification "test ping" fires (closest timed), Nudge.wav plays
# → ~/.cache/td/fired gains a row for it
# → ~/.cache/td/added gains rows for all four tasks (first-seen)

# 4. Re-run tick — must NOT re-fire
~/.config/helix/bin/td tick   # silent

# 5. Edit a task — rehash + re-arm
sed -i 's/test ping/test ping edited/' ~/tasks/day.md
~/.config/helix/bin/td tick   # notification fires again

# 6. Listing
~/.config/helix/bin/td list
# stdout shows:
#   # ACTIVE
#   .../day.md:N: refactor td parser #active
#   # TODAY
#   .../day.md:N: pay rent <...> #today
#   # TODO
#   .../day.md:N: call jon
cat ~/.cache/td/last-list.md   # same content

# 7. Sort by modified
~/.cache/td/added -> inspect; then:
~/.config/helix/bin/td list --sort modified
# order within each group should reflect file mtime, newest first

# 8. Clock-fake for tests
TL_NOW='2026-10-11 18:30' ~/.config/helix/bin/td tick
# → "pay rent" fires

# 9. Built-in tests
~/.config/helix/bin/td test   # unittest run, exits 0

# 10. Uninstall
~/.config/helix/bin/td uninstall
termux-job-scheduler --pending   # job 7421 gone
```

Helix side:

- Open `~/tasks/day.md`, press `space . t`, confirm `- [ ] <...>` template is inserted at the cursor; type `#active refactor td parser`.
- Press `space . l`, confirm the reusable buffer opens with grouped list, "refactor td parser" at the top of ACTIVE.
- Move the cursor to any `path:line:` row, press `gf`, confirm you land on that line in the source file.
- Edit a task in the source, save, press `space . l` again — the same buffer refreshes (no new window).
- Press `space . L` → same buffer, now sorted by file mtime.

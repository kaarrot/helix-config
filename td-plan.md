# TODO Scheduler — `td`

## Context

You want two complementary things in one tool:

1. **Timed reminders** — `- [ ]` todos with an org-style `<YYYY-MM-DD HH:MM>` stamp that fire a Termux notification at that time, reliably, regardless of what's running. Today your notifications only fire from Emacs (`~/dotemacs/emacs:1907` → `my-termux-notify` + `appt`), which is silent whenever Emacs isn't running.
2. **Long-running backlog with lightweight state** — tasks tagged `#active` (currently working on), `#today` (plan to tackle today), or no tag (plain backlog). State is just a hashtag — no checkbox gymnastics, so your existing `x` key still toggles `[ ]`↔`[X]`, and future `#tag` filtering reuses the same mechanism.

The design mirrors `~/.config/helix/bin/tl`: pure Python stdlib, plain-text data in `$TL_DIR`, env-var config, no deps.

## Approach

1. Store scheduled todos + stateful backlog as regular bullets in the existing `~/tasks/*.md` files. State is tag-based (`#active`, `#today`); timestamp is optional and org-style.
2. Register **one** periodic `termux-job-scheduler` job (every 15 min, the Android minimum, `--persisted true`). The job runs `td tick`, which fires any timed items due now.
3. Track already-fired reminders in `~/.cache/td/fired` (sidecar, hashed by line text so edits re-arm). Track task first-seen time in `~/.cache/td/added` so "sort by recently added" works even though markdown has no creation stamp.
4. `td list` writes a grep-like `path:line:text` view to `~/.cache/td/last-list.md`. Open that file in Helix — it's a normal buffer (`gf` jumps to source), and `auto-reload = true` means re-running `td list` refreshes it in place. One reusable buffer, not a stream of popups.
5. No new config file. Reuse `TL_DIR` env var; add `TD_CATCHUP_H` and `TD_LEAD_MIN` env vars only (both have defaults).

## Line format

Date (if any) comes after the task text, org-style. State is a tag anywhere after the checkbox:

```
- [ ] call jon                                  # plain backlog, no fire
- [ ] #active refactor td parser                # long-running, surfaced
- [ ] #today pay rent <2026-10-10 18:30>        # today + timed
- [ ] #active overhaul tests <2026-11-01 10:00> # active + timed
- [ ] buy chili seeds #errand                   # free-form tag (future filter)
- [x] took bins out <2026-10-09 08:00>          # done
- [!] call mom                                  # user-marked ignore
```

Parsing rules (match `tl`'s tolerant style — unparseable lines pass through untouched):

- Line is a candidate iff `^\s*- \[[ xX!]\]\s+` matches.
- Timestamp regex: `<(\d{4}-\d{2}-\d{2}) (\d{1,2}:\d{2})>` — same `YYYY-MM-DD HH:MM` as `tl`.
- Tags: `#\w+` anywhere after the checkbox. `#active` and `#today` are known states; anything else is a user tag.
- Fire eligibility: `[ ]` AND has `<timestamp>` AND `#active` or `#today` OR no state tag. `[x]`/`[X]`/`[!]` always skipped.
- State without timestamp = never fires, just surfaces in `td list`.

Coexistence with `tl`: `tl`'s date regex requires a date at the **start** of the entry portion (`YYYY-MM-DD HH:MM - ...`). `td`'s date is inside `<...>` and after prose. No ambiguity.

Your existing `x` keybinding (sed-toggle `[ ]`↔`[X]`) still works for marking done — no change.

## Sidecars

### `~/.cache/td/fired` — fired-reminder dedup

Append-only, TAB-separated: `due_iso \t sha1(path\tline_text_normalised) \t short_text`. Rehashing the line text at fire time means if you edit the task before it fires, the hash changes and it re-arms as a new reminder. `td tick` prunes entries older than `catchup_hours * 2` on each run.

### `~/.cache/td/added` — first-seen timestamp per task

Append-only, TAB-separated: `first_seen_iso \t sha1(same as above) \t short_text`. Populated by `td tick` and `td list` the first time a new hash appears. Needed because markdown has no creation stamp — without this, "sort by recently added" would be impossible.

When a task's text is edited, its hash changes → treated as a new task (new first-seen time). Deliberate: you can "re-prioritise" by rewording. When a task is removed or ticked off and its hash disappears from scans for N days, its sidecar row is pruned.

### `~/.cache/td/last-list.md` — reusable listing buffer

Overwritten by every `td list` call. Open once in Helix (`:open <path>`), re-runs refresh in place thanks to `auto-reload = true`.

## Firing mechanism

Single periodic job:

```
termux-job-scheduler \
    --job-id 7421 \
    --script ~/.config/helix/bin/td-tick \
    --period-ms 900000 \
    --persisted true
```

`td-tick` is a two-line shim that `exec`s `td tick` under the right env. `td install` writes it and registers the job; `td uninstall` removes both.

**Window on each tick:** fire everything where `due ≤ now AND due ≥ now − catchup_hours AND hash ∉ fired`. Default `catchup_hours = 6`. Rationale: Doze mode, airplane mode, and reboots routinely cause missed ticks; a strict `[last_tick, now]` window silently drops reminders. 6h caps the "returning from a day away" blast; configurable via `TD_CATCHUP_H`.

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
| `td tick` | What the job calls. Scan `$TL_DIR/*.md` + `*.txt`, fire due items, update `fired` + `added` sidecars. |
| `td list [--state S] [--sort added\|modified] [--tag T]` | Write grouped listing to `~/.cache/td/last-list.md` and stdout. |
| `td next` | Print the single next-timed-due item (for statusline / one-off checks). |
| `td new [--in DUR] [--state S]` | Print `- [ ] [#state ]<YYYY-MM-DD HH:MM> ` prefix for pipe/insert; `--in 1h` default. `--state active` or `--today` omits the timestamp. |
| `td fire <path>:<line>` | Fire that line manually (testing). |
| `td test` | Built-in unittest, mirrors `tl test`. |

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

- **Doze mode skips ticks** → `catchup_hours` window; `--persisted true` survives reboot.
- **File edited mid-tick** → `fired` sidecar hashes the current line text; if it changed since scheduling, the new hash re-arms it as a new reminder.
- **Duplicate job on reinstall** → fixed `--job-id 7421`; `td install` cancels first.
- **DST spring-forward** at 02:30 → that wall-clock never happens; it will fire on the next tick after 03:00 (within the 6h catchup). Document.
- **DST fall-back** at 02:30 → wall-clock happens twice; sidecar dedup by hash makes it fire once.
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

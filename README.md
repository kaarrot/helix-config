# Helix config

My Helix setup on Termux, plus `td` (todos, reminders, the agenda) and `tl`
(time log), driven by the keys under `space ,`. How they work:
[docs/agenda.md](docs/agenda.md); every key: [docs/keys.md](docs/keys.md).

## What td / tl need

**Always**

- **My Helix fork** (`main-kuba`, built from `~/SRC/helix`), as `~/bin/hx`
  with its runtime next to it (see the symlink below). Stock Helix rejects
  `config.toml`: `space , a` / `A` call `fold_all`, which only the fork has.
  The fork also does the agenda folding (`runtime/queries/td/folds.scm`) and
  the `-bold` in `themes/github_light.toml` that keeps dates in bold tasks
  plain.
- **bash**: `editor.shell` is `bash -lc`, and the prompt keys (`space , n`,
  `N`, `O`) read what you type from `$BASH_EXECUTION_STRING`.
- **Python 3**, standard library only, for `bin/td` and `bin/tl`. No config
  files: `$TL_DIR` (default `~/tasks`) and `$TD_FILE` (default
  `~/tasks/todo.md`) are the only settings that matter day to day.
- **harper-ls** (optional): the language server for task files. Without
  it, Helix only warns.

**Reminders (Termux on Android only)**

- The **Termux:API** app and `pkg install termux-api`: notifications
  (`termux-notification`, `termux-open`, `termux-wake-unlock`).
- `pkg install ecj dx`: they build `bin/TdAlarm.java`, the exact-alarm
  helper.
- Termux and Termux:API set to *Unrestricted* battery use.
- Run `bin/td install` once, and again whenever `bin/TdAlarm.java` changes.

Steps and checks: [Quick start](docs/agenda.md#quick-start).

## Highlighting task files

`languages.toml` makes `~/tasks/*.md` and the agenda (`~/.cache/td/agenda.md`)
a language of their own, `td` (markdown's grammar), so their colours don't
touch other markdown. Its queries are in `runtime/queries/td` and
`td.inline`, and add only td's rules on top of upstream's markdown ones.

`td.inline` builds on upstream's `markdown.inline` queries, but an
`; inherits:` line can't name a language with a dot in it. So
`runtime/queries/markdown_inline` is a symlink to them, a relative one:
`../../../../bin/runtime/queries/markdown.inline`, which is
`~/bin/runtime/queries/markdown.inline`. If the link is broken, task lines
keep td's own colours but lose markdown's inline ones (bold, italics, code,
links).

### Setting up the symlink

Git keeps the link itself. It only needs Helix's runtime at `~/bin/runtime`,
the place `~/bin/hx` looks for it anyway:

```sh
ln -s ~/SRC/helix/runtime ~/bin/runtime
```

Check it:

```sh
ls ~/.config/helix/runtime/queries/markdown_inline/   # highlights.scm  injections.scm
hx --health td                                        # Highlight queries: ✓
```

If Helix's runtime lives somewhere else, point the link at it instead,
keeping the link's name:

```sh
ln -sfn /path/to/helix/runtime/queries/markdown.inline \
  ~/.config/helix/runtime/queries/markdown_inline
```

That changes a tracked file, so don't commit it.

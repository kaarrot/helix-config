# Plan: time tracking in todo.md

Status: built 2026-10-21 (see docs/keys.md, "Time in todo.md"). Kept as the
record of the design; the `P` step differs from the first draft as noted below.

Changed after the user tested it (2026-10-21): a todo's "block" (lines
indented deeper) became its **section**: the lines under it up to the next
todo at its indent or less, or a heading, so notes need no indent (the
user writes them at the left, after a blank line). A sub-todo's section
also ends at a line indented less than it. `space , i` lines the entry up
with the todo. The rules below still say "block"; docs/keys.md has the
current ones.

The workflow it is for: `space , q` adds a todo, you jot notes under it,
track time on it, and later `space , P` turns it into a file task that takes
the notes and the time along.

```
- [ ] prep slides
  check last year's deck
  2026-10-21 14:37 - 15:10 = 0h 33min  made outline
  2026-10-21 16:00 -                    ← space , i, cursor anywhere in the block
- [ ] call mom
```

## Rules

- **Entries in todo.md.** A line in todo.md is a time entry if it is shaped
  like one (as in task files) and has no checkbox. A checkbox line is always
  a todo, so `- [ ] 2026-10-12 09:00 - prep slides` stays a todo and is never
  ended or counted. Nothing changes on td's side: td already leaves non-bullet
  lines in todo.md alone (no agenda row, no reminder).
- **A bullet's block** is the bullet line plus the lines after it that are
  indented deeper than it. Blank lines count when an indented line follows
  them (as in markdown); trailing blank lines don't. A line belongs to the
  innermost checkbox bullet whose block holds it, so a sub-bullet
  (`  - [ ] buy paper`) has a block of its own inside its parent's.

## Keys

- **`space , i`, cursor in todo.md:** ends what is running, as today
  (entries in todo.md included now). Then the new entry goes:
  - on a bullet or anywhere in its block: on a new line at the end of the
    block, indented like the block's first indented line, or 2 spaces
    deeper than the bullet if the block has none;
  - anywhere else: a plain entry, on the cursor's line if it is blank,
    otherwise on a new line below it.

  Normal mode at the line end, as today. In other task files the entry
  still goes on a new last line.
- **`space , o` / `O`, running entry in todo.md:** a `# heading` above it
  would break the list, so what you did goes at the end of the entry line
  (`… = 0h 33min  made outline`). It goes after two spaces, or after ` - ` if
  the entry already has a note. `o` leaves you in insert mode there; Esc
  leaves the two spaces, which do no harm. Entries in task files keep their
  headings.
- **`space , u` in todo.md:** works out durations again, on entries only;
  todos are left alone.
- **`space , P` in todo.md:** as today (the file, its `# [S] title`, the
  bullet stays as the link), and also *moves* the bullet's block, without the
  bullet line itself, to the end of the file. Its common indent is removed, so
  entries become top-level and sub-bullets become the file's subtasks. An
  existing file gets the block at its end; pressing `P` again later moves
  only what was added since. A running entry moves too, and `tl` finds it
  in the file. `P` on an agenda row is unchanged: it only opens the file.
- **Summary (`l`, `L`):** todo.md is listed as `todo` with no title (today
  it would take the first bullet's text). The heading for an entry in a block
  is its bullet's text, without the checkbox. Plain entries have none.
- **`I`, `r`:** nothing to change: they find todo.md's entries once the rule
  above is in.

## Changes

**bin/tl**
- Replace the `is_td_inbox` skips (`entry_starts`, `stop_files`,
  `end_latest`, `cmd_summary`, `cmd_stop -`, `cmd_close`, `cmd_edit`) with the
  checkbox rule: one helper, `parse_in(path, line)`, or a flag on `parse`.
  `recent` gets it too.
- Block helper: `block(lines, i)` → (bullet index, last line of the block,
  indent to use), or None when line i is in no block. td needs the same
  thing for `P`. td already imports tl (`_tl()`), so td uses tl's helper.
- `tl running --from F:LINE` keeps the line in `~/.cache/tl/from`. `tl next`
  no longer deletes that file.
- New `tl start - --file F`: the whole buffer in, the buffer out with the
  new entry in place (the rules above for todo.md, a new last line
  elsewhere). It writes F:LINE of the entry to `~/.cache/tl/goto` and deletes
  `~/.cache/tl/from`. Plain `tl start` still prints the stamp.
- `cmd_edit` (`o`) and `end_latest` (`O`): for an entry in todo.md, put the
  note on the entry line instead of calling `add_heading`.
- Summary: todo.md's title, and the bullet as the heading.

**bin/td**
- `td promote --from F:LINE` (the line on stdin, as before) also keeps an
  inbox bullet's place and its file in `~/.cache/td/cut`.
- New `td promote --cut - --file F`: the whole buffer in; in todo.md, the
  kept bullet's block comes out of it and goes to the end of the file *on
  disk*, without its shared indent and leading blank lines.
- Changed from the first draft (a `td carry` step piping the block into
  the file's buffer): a whole-buffer pipe moves the cursor to the end, and
  neither `:earlier` nor the jumplist brings it back (tested), so `P`
  would have moved the cursor even with nothing to move. On disk, an open
  unmodified buffer auto-reloads; one with unsaved edits refuses to save
  over the change (tested, documented in keys.md).

**config.toml**
- `i`: `--from %{buffer_name}:%{cursor_line}`. Replace `goto_last_line`,
  `open_below`, `normal_mode` and `:insert-output tl start` with
  `select_all`, `:pipe tl start - --file %{buffer_name}`,
  `collapse_selection`, `:write!`, `:open %sh{cat ~/.cache/tl/goto && rm …}`,
  `goto_line_end`. `tl` writes the line itself, so Helix's list continuation
  (`- [ ] `) and auto-indent can't change it.
- `P` (as built): `extend_to_line_bounds`, `:pipe-to td promote --from …`,
  `select_all`, `:pipe td promote --cut - …`, `collapse_selection`,
  `:earlier %sh{…agenda… && echo 1 || echo 0}`, `:update`, `:open` where
  `P` goes, as before. The old leading `:update` is gone, so todo.md is
  saved once, after the cut; on the agenda the undo leaves nothing to save.

## Gotchas to test for

- One buffer saved twice in one key needs `:write!` the second time (todo.md
  in `P`; in `i` when the running entry was in the same buffer).
- `:pipe` always marks the buffer modified.
- Unsaved edits: a just-typed note in todo.md, a running entry not yet saved,
  the task file already open with unsaved edits when `P` runs.
- `P` on a bullet that has no block yet: the same as today.
- A block that holds the running entry: after `P`, `I` and `o` find it in the
  file.

## Tests

- tl and td unit tests: the checkbox rule, block bounds (blank lines,
  nesting, tabs), where `start -` puts the entry, the note on the line for
  `o`/`O`, the summary heading, `promote -`/`carry -`. Rewrite the tests
  that say todo.md passes through unchanged.
- Real Helix in a pty with a scratch HOME (never the real `~/tasks`):
  `q` → note → `i` → `o` → `i` → `P`, from saved and unsaved buffers, plus
  `i` in an ordinary task file to check that it is unchanged.

## Docs

`docs/keys.md` (the `i`, `o`, `O`, `u`, `P` rows and the "todo.md is not a
task file" line), `docs/agenda.md` wherever it says the same, and the help
text in `bin/tl`.

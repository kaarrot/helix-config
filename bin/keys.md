# `td` / `tl` keys

Every key under `space ,` (`[keys.normal.space.","]` in `../config.toml`)
and the `+`/`-` stamp keys in `[keys.normal]`. `td test` checks that this
file and the config list the same keys, so add a row here whenever you add
or remove a key there.

Design notes and the agenda format: [agenda.md](agenda.md).

All keys below except `+`/`-` are pressed after `space ,`.

## Time log (`tl`)

| Key | What it does |
|---|---|
| `i` | Clock in: stop any running entry, then start a new `YYYY-MM-DD HH:MM - ` line at the end of the buffer for your note |
| `o` | Clock out: save all, prompt `# done:` for what you did; Enter ends the running entry with that text as its heading, Esc does nothing |
| `r` | Recently modified task files, newest first, in a popup |
| `S` | Per-day time summary of all task files, or just this file if it is outside `~/tasks` |

## Todos (`td`)

| Key | What it does |
|---|---|
| `t` | Open the inbox, `~/tasks/todo.md` |
| `a` | Agenda, newest-added bullets first |
| `A` | Agenda, most recently changed first |
| `Y` | Toggle `[ ]` ↔ `[Y]` (today) |
| `L` | Toggle `[ ]` ↔ `[A]` (active) |
| `x` | Toggle `[ ]` ↔ `[x]` (done). On a line with a `++Nu` / `.+Nu` repeater, move the date forward instead |
| `p` | Jump to the bullet's own file. From the agenda, go to the bullet's line in todo.md when there is no file. Never creates a file |
| `P` | Give the bullet its own file, `~/tasks/<slug>.md` (reused if it exists), and open it |
| `s` | Stamp the line. No date: add today's date and the current time. Cursor on the date: fix only the weekday. Cursor elsewhere: change the date to today and keep the time |
| `Enter` | Run a reminder check now, the same one the 15-minute job runs |

`Y`, `L` and `x` also work on agenda rows and in dedicated files, and they
update the matching bullet in todo.md.

## Moving a stamp (normal mode, no `space ,`)

`+` moves the stamp (`YYYY-MM-DD Xxx HH:MM`) on the cursor's line later and
`-` moves it earlier, by the part under the cursor. The cursor stays on that
part, so pressing again keeps moving it. The weekday follows the date, and
one undo reverts one press. A line with no stamp is left alone.

| Key | What it does |
|---|---|
| `+` | Later by one year, month, day, hour, or 5 minutes, whichever the cursor is on. On the weekday or anywhere else on the line: one day |
| `-` | The same, earlier |

Minutes land on multiples of 5 (`09:32` → `09:35` / `09:30`). Hours past
midnight change the day; a month from the 31st lands on the month's last day.

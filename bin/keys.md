# `space ,` keys

Every key under `space ,` in `../config.toml` (`[keys.normal.space.","]`).
`td test` checks that this table and the config list the same keys, so
add a row here whenever you add or remove a key there.

Design notes and the agenda format: [agenda.md](agenda.md).

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

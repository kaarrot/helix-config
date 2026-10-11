# Rust DAP Debugging in Helix on Termux

How to get `lldb-dap` working inside Helix on Termux, with Rust pretty-printers
that actually render collection contents inline (e.g. `vec![1,2,3]` shows as
`([0] = 1, [1] = 2, [2] = 3)` instead of `size=3`).

## 1. Install `lldb-dap`

Termux ships `lldb-dap` inside the `lldb` package:

```sh
pkg install lldb
```

Helix's built-in Rust template hardcodes the `lldb-dap` binary name; before
installing it, `hx --health rust` shows:

```
Configured debug adapter:
  ✘ 'lldb-dap' not found in $PATH
```

## 2. Fix the Python dependency

`lldb-dap` is dynamically linked against `libpython3.13.so`. If the system
still has Python 3.12, you get:

```
CANNOT LINK EXECUTABLE "lldb-dap": library "libpython3.13.so" not found
```

Upgrade Python:

```sh
pkg install python   # → 3.13.x
```

Verify:

```sh
lldb-dap --help | head
```

## 3. Load Rust pretty-printers via `initCommands`

`lldb-dap` does **not** read `~/.lldbinit` by default. The Rust formatter
scripts must be injected through the DAP launch request's `initCommands`.

Override Helix's built-in Rust debugger template in `~/.config/helix/languages.toml`:

```toml
[[language]]
name = "rust"
auto-format = true
roots = ["Cargo.toml", "Cargo.lock"]

[language.debugger]
name = "lldb-dap"
transport = "stdio"
command = "lldb-dap"

[[language.debugger.templates]]
name = "binary"
request = "launch"
completion = [ { name = "binary", completion = "filename" } ]
args = { program = "{0}", initCommands = [
  "command script import /data/data/com.termux/files/usr/lib/rustlib/etc/lldb_lookup.py",
  "command source -s 0 /data/data/com.termux/files/usr/lib/rustlib/etc/lldb_commands",
  "type summary add -c -x \"^(alloc::([a-z_]+::)+)Vec<.+>$\" --category Rust",
  "type summary add -c -x \"^(alloc::([a-z_]+::)+)VecDeque<.+>$\" --category Rust",
  "type summary add -c -x \"^&(mut )?\\[.+\\]$\" --category Rust",
] }
```

Paths point at `$(rustc --print sysroot)/lib/rustlib/etc/`. On Termux that
resolves to `/data/data/com.termux/files/usr/lib/rustlib/etc/`.

## 4. Why the extra `-c` overrides are needed

The default Rust `Vec` summary returns just `"size=N"`. Helix's variables
popup is flat — it does **not** expand synthetic children — so without inline
rendering you only see `size=2` and nothing about the elements.

The three `type summary add -c ...` lines replace the size-only summaries
with ones that inline children (`-c` = `--inline-children`). After this:

```
v: alloc::vec::Vec<int, alloc::alloc::Global> = ([0] = 1, [1] = 2, [2] = 3)
```

Add the same pattern for any other collection types you care about, e.g.
`HashMap`, `BTreeMap`, etc. — match the regex shipped in `lldb_commands`.

## 4a. Why both pieces are needed (synthetic provider + `-c`)

`lldb_lookup.py` and the `-c` summary overrides do different jobs and **both
are required** for the Helix popup to show collection contents:

| Piece | Job |
|---|---|
| `lldb_lookup.py` + `lldb_commands` | Register **synthetic providers** — Python that walks `Vec`'s internal `RawVec { ptr, cap }` + `len` and exposes the elements as `[0]`, `[1]`, … so LLDB knows they exist. |
| `-c` summary overrides | Tell LLDB to **inline those children into the displayed value** instead of showing only the type-specific summary string (`size=N`). |

Without `lldb_lookup.py`, a `Vec<i32>` is just an opaque struct of
`buf: RawVec, len: usize` — there are no `[0]`, `[1]` children to inline,
so `-c` would have nothing to show. Without `-c`, the children exist but
the popup only shows the summary string `size=N` because Helix's flat
variables view doesn't expand synthetic children.

In **DAP**, Helix only displays the *value* field in the popup. `-c` is the
unlock: it pushes the children into the value string so a flat-popup client
like Helix can see them.

Note: `lldb-dap` does **not** read `~/.lldbinit`, so the `command script
import` of `lldb_lookup.py` in `initCommands` is genuinely required for
DAP — it's not redundant with the optional `~/.lldbinit` below.

Quick demo from the CLI (after the `~/.lldbinit` from step 5 is in place):

```
# Without -c
(alloc::vec::Vec<int, alloc::alloc::Global>) v = size=3 {
  [0] = 1
  [1] = 2
  [2] = 3
}

# With -c
(alloc::vec::Vec<int, alloc::alloc::Global>) v = ([0] = 1, [1] = 2, [2] = 3)
```

Both forms look fine in CLI `lldb` because it renders the expanded children
block; only the second survives DAP transit into Helix's popup.

## 5. Optional: `~/.lldbinit` for CLI lldb

For interactive `lldb` / `rust-lldb` sessions outside DAP, drop this in
`~/.lldbinit` so CLI debugging gets the same formatters:

```
command script import "/data/data/com.termux/files/usr/lib/rustlib/etc/lldb_lookup.py"
command source -s 0 "/data/data/com.termux/files/usr/lib/rustlib/etc/lldb_commands"
```

CLI `lldb` does read `~/.lldbinit` (unlike `lldb-dap`).

## 6. Verify

```sh
hx --health rust
```

Should show:

```
Configured debug adapter:
  ✓ /data/data/com.termux/files/usr/bin/lldb-dap
```

In Helix: open a Rust file, `:debug-start`, pick `binary`, point at
`target/debug/<binary>`. Locals show inline collection contents in the popup.

## Red herrings encountered along the way

- **Catch-all summary line** `type summary add -F _ -e -x -h "^.*$"` — present
  in older rust toolchains' `lldb_commands`. Doesn't actually affect `Vec`
  rendering because type-specific rules always win over catch-all.
- **Wrapper script `lldb-dap-rust`** on Debian — only fixes the Debian-packaged
  LLVM 14 lldb's broken Python path. Termux's LLVM 21 doesn't have that bug.
- **Embedded Python interpreter** — works fine on Termux once `python` is on
  3.13. Verified via `script print(sys.version)` in `lldb`.

## Helix UI caveat

Helix's debug variables popup is minimal in 25.07: no expand/collapse key, no
scroll once focus is lost. For deep inspection, use `:debug-eval <expr>` or
drop to CLI `lldb` in a tmux pane. The inline-children summaries get you most
of the way for everyday Rust debugging.

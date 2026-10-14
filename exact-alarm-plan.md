# td: exact-time reminders

Status (2026-10-14): **phase 1 built** (`bin/TdAlarm.java`, `bin/td`; the
user doc is [bin/agenda.md](bin/agenda.md)). Phase 2, the fork's save hook,
is dropped: opening the agenda arms a hand edit. `space , Enter` (save and
tick) is gone too; it was only for testing. Proven
first in a throwaway `~/alarm-test`: an Android alarm set as com.termux
whose notification arrived on time with the screen off (+115 ms after ~45
min idle). Built with the two bugs below fixed and reminders gated behind
`TD_TERMUX`.

## The idea

The alarm carries no reminder data: it only wakes `td tick` at the right
moment, and the tick keeps deciding what is due. So a stale alarm just runs
a tick that finds nothing. The alarm replaces the 15-min job: there is no
periodic safety net.

```
any tick ──▶ fire what is due ──▶ arm the next alarm (or cancel if none)

T − 15 s   alarm ─▶ TermuxService wake_lock     (phone stays awake)
T          alarm ─▶ td-tick --alarm ─▶ notification ─▶ arm next ─▶ unlock
```

### One alarm, many reminders

Only one alarm exists at a time: the one for the nearest future reminder.
Nothing else is lost. The reminders live in the task files, and every tick
rescans all of them and re-arms the earliest. Each alarm's tick then arms
the next one, so the chain walks through every reminder in order.

Example, with reminders at 11:00, 14:00 and 18:00 in the files:

- The alarm is set for 11:00.
- At 10:30 you add 10:45 and save. The tick moves the alarm to 10:45. The
  11:00, 14:00 and 18:00 reminders stay in their files.
- At 10:45 the tick fires that reminder and arms 11:00. At 11:00 it fires
  and arms 14:00, then 18:00 the same way.
- If you mark the armed reminder done or delete it, the next tick moves the
  alarm to the next reminder, or cancels it when none is left.
- Reminders at the same minute share one alarm, and one tick fires them all.
  Two stamps at the same minute in the same file are the exception, until
  the same-key bug below is fixed.

Why not one alarm per reminder: td would have to keep a list of alarms and
cancel each one when its stamp is edited, moved or deleted. That list would
duplicate the files and drift from them. One alarm recomputed from the files
on every tick has nothing to keep in sync.

With no periodic job, a broken chain stays broken until the next tick runs.
That happens when the phone reboots, Termux is force-stopped, or arming
fails. Opening the agenda (`space , a` / `space , A`) runs a tick, as does
any save or td key. So the usual "what's next" look re-arms the chain, and
reminders that came due in the gap fire then, late. No boot script is needed.

## Changes

1. **`bin/TdAlarm.java`**: `~/alarm-test/AlarmTest.java`, with the script
   fixed to the `td-tick` shim and the arguments `--alarm`/`--alarm-nolock`
   instead of the due time. Interface: `set EPOCH_MS` and `cancel`. It keeps
   the quiet `setExactAndAllowWhileIdle` type, so there is no alarm icon.

2. **`cmd_install`** (`bin/td`):
   - builds the jar into `~/.cache/td/td-alarm.jar` with `ecj` + `dx`;
   - writes the shim so it forwards its arguments (`tick "$@"`);
   - cancels job 7421 instead of registering it, then runs one tick to arm
     the first alarm.
   - If `ecj`/`dx` are missing, it stops with that message and leaves the
     job in place.

3. **`cmd_tick`**:
   - takes an `flock` on `~/.cache/td/tick.lock`, because ticks can now come
     from the alarm, the job, saves and keys at the same moment;
   - `TD_LEAD_MIN` defaults to 0 (td-plan.md already says 0). The 15 only
     made up for the job's timing;
   - after the fire loop it arms the earliest future `due − lead` not in
     `fired`, or cancels when there is none. That calculation is a pure
     function, so the tests can cover it; under `TD_DRY_RUN` nothing is armed;
   - with `--alarm`, it runs `termux-wake-unlock` at the end.

4. **Re-arm when reminders change, and when the agenda opens**: done in
   `main()`, so one place covers every command. After `list` (the agenda
   keys `space , a` / `A`), `stamp`, `shift`, `toggle`, `set`, `rename`,
   `file`, `promote` or `new`, td starts a detached `td tick`. Doing it on
   `list` restarts the chain after a reboot without a boot script.
   - stdio goes to `/dev/null` and it runs in a new session, so `:pipe` keys
     don't wait for it;
   - it starts after a ~2 s delay, so a key's trailing `:update` has written
     the file first.

5. **Helix fork (phase 2, dropped)**: a plain `:w` after a hand edit is the
   one change td never sees. In `handle_document_write`
   (`helix-term/src/application.rs:636`), after a successful save, spawn
   `$HX_ON_SAVE <path>` if that env var is set (`tokio::process::Command`,
   not awaited by the editor). Point it at a small script that runs `td-tick`
   when the path is under `$TL_DIR` or is `$TD_FILE`. Helix stays unaware of
   td. Not built: hand edits get armed by opening the agenda or the next td
   key.

## Gotchas

- One helper call takes about **1.3 s** (app_process start-up), which is why
  every tick after a key or save runs in the background.
- Edits made with `:pipe` only reach disk when the buffer is saved. That's
  why the td-side re-arm waits ~2 s.
- `termux-wake-unlock` also releases a wake lock you took yourself with
  `termux-wake-lock`.
- A reboot or a force-stop of Termux clears the alarm, and nothing re-arms
  it until the next tick, normally the next agenda open (see "One alarm,
  many reminders").
- A failed arm also breaks the chain silently, so td should log it, and
  `td next` should show the armed time.
- Two bugs that the 15-min slack used to hide:
  - two stamps at the same minute in one file share a key, so only one
    fires;
  - a reminder lands in `fired` even when `termux-notification` fails.

## Phases

1. **td only**: changes 1–4, plus logging a failed arm. Everything done
   through td keys fires on time; a hand edit saved with `:w` is armed only
   at the next tick (opening the agenda).
2. **Fork hook**: change 5. Dropped.
3. Optional: fix the two bugs (done in phase 1), and have `td next` show the
   armed time.

## Test plan

- `td test`: next-fire calculation, lead default 0, nothing armed in dry
  run, lock.
- Device: stamp a reminder 2 minutes out with `space , s`, lock the screen,
  and check the notification arrives on the minute. Then leave one overnight.
- `termux-job-scheduler -p` no longer lists job 7421.

## Choices made

- Lead default 0, with `TD_LEAD_MIN` for warning offsets.
- Quiet alarm (no icon), not the alarm-clock type.
- No 15-min safety net; opening the agenda re-arms after a reboot.
- No fork hook.
- The two bugs fixed in the same pass, plus pruning the cache files.

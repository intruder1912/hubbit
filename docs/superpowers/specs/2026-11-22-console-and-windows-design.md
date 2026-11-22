# Design: Windows readiness + interactive command console

Date: 2026-11-22 · Status: proposed · Roadmap: #8

## Intent

The hub is out of reach for now, so this batch prepares the work that needs no hardware:

1. **Windows readiness.** The kids notebook runs Windows, and #4 (hardware check there) should
   be a short, boring session with nothing left to fix on the spot.
2. **Interactive console.** The robot is driven by typed commands in one long session. It
   connects once and disconnects only on `exit` (or Ctrl+C). It is mainly **for young programmers**: simple
   words, forgiving input, helpful errors. It also has a **raw mode** for the adult
   (direct motor/sensor access for experimenting).

## Goals

- One command `uv run boost-console` that works the same on macOS, Linux and Windows.
- Simple vocabulary for kids: `forward [s]`, `back [s]`, `left [deg]`, `right [deg]`,
  `led <color>`, `color`, `distance`, `stop`, `help`, `exit`.
- Raw mode (`raw` / `simple` to toggle) for the adult: per-port motor commands, angled moves,
  sensor dump, battery.
- Long sessions: one connection for the whole session. A dropped link is detected and offered
  as `reconnect` without leaving the console.
- `stop` and `exit` always win. They do not wait behind a running move.
- The parser and executor are unit-tested with fake hubs, without hardware, on all three OSes in CI.

## Non-goals (this round)

- Full-screen TUI (textual) → later issue, built on the same core.
- Live arrow-key driving (comes with the TUI).
- Scripting/recording of command sequences (could come later).
- Replacing pylgbst, or using BOOSTreveng code.

## Anti-goals

- A console that a 10-year-old can crash with a typo, or that leaves motors running.
- Reconnecting silently in the middle of a move.
- OS-specific code paths in the console (beyond what prompt_toolkit hides).

## Constraints

- Hardware safety rules from CLAUDE.md: default speeds ≤ 50 %, motors stop on any error and on exit.
  Raw mode clamps speed to ±100 % and duration to ≤ 10 s per command.
- Each motor call blocks ~0.28 s+ (BLE round trip), so commands need a background thread
  for `stop` to work.
- pylgbst stays pinned. `patch_pylgbst()` keeps applying.
- Kids scripts must keep using only `Robot`. The console is a tool, not a kids mission.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| A | stdlib `cmd` loop | No dependency; no history/completion on Windows; plain |
| **B (chosen)** | `prompt_toolkit` prompt | One small pure-Python dependency, good Windows support, history, Tab completion, bottom status bar |
| C | `textual` full-screen TUI | Most kid-appealing (buttons, live sensors, arrow keys), 2–3× effort, harder to test → **later issue** |

The user picked B first, with C as a later issue. The core is shared, so C only adds a front end.

## Design

### Layers

```
boost-console (prompt_toolkit UI)       later: boost-tui (textual UI)
        │                                       │
        └────────── lego_boost.console core ────┘
             parser  →  Command(name, args)
             executor: one worker thread, queue, stop/exit priority
             session:  owns the Robot connection, detects drops, reconnect
                         │
                    lego_boost.kid.Robot (+ small additions)  →  pylgbst
```

- **Parser** (`lego_boost/commands.py`, pure, no I/O). It turns a line into a `Command`, or into an
  error that suggests the closest known word ("Did you mean `forward`?"). It is case-insensitive and
  accepts numbers with a `,` or `.` decimal separator. Words come from an alias table, so the German
  words from #7 (`vor`, `zurück`, `links`, `licht`) can be added there without touching the logic.
- **Simple commands** map to `Robot` methods. `left`/`right` take **degrees** (default 90). They are
  converted with the existing calibration (`QUARTER_TURN_SECONDS`), as a linear approximation, and
  the turn is documented as approximate.
- **Raw commands** are only accepted in raw mode: `motor A|B|AB|C <speed%> <seconds>`,
  `angle A|B|AB|C <degrees> [speed%]`, `sensors`, `battery`, `hub` (name/firmware/voltage).
- **Executor.** Commands go into a queue and are run by a single worker thread, one at a time.
  `stop` empties the queue and calls `Robot.stop()` straight from the UI thread. `exit` = stop +
  close the session. Errors in a command are printed and the console keeps running.
- **Implementation note (batch 5).** pylgbst allows only one pending request, so only the
  worker thread talks to the hub. `stop` from the UI thread just cancels and wakes the worker,
  which stops the motors itself. Moves start with `wait_complete=False` and are waited for in
  0.05 s steps. A per-command watchdog (expected duration + 5 s) marks the hub as lost, because
  `is_alive()` only turns False after a failed write. Lives in `lego_boost/commands.py` (parser)
  and `lego_boost/session.py` (session + worker).
- **Session.** It connects once at start (with the usual "press the green button" hint). Before each
  command it checks `hub.connection.is_alive()`. If the link is gone it prints a clear message and
  only accepts `reconnect` / `exit`. Disconnect happens only on `exit`, on Ctrl+C or Ctrl+D, or
  at process end (`with Robot()`).
- **UI (prompt_toolkit).** It shows a mode-coloured prompt (`robot>` / `raw>`) and keeps history in
  `~/.lego_boost_history` (via `pathlib.Path.home()`, which works on all OSes). It has Tab completion
  for command words and colours, and a bottom bar with connection state, mode, battery and last colour.
  `help` lists the commands of the current mode, with an example each.

### Robot additions (kid API stays backwards compatible)

- `turn_left(degrees=…)` / `turn_right(degrees=…)` are keyword alternatives to seconds. Existing
  missions are unchanged.
- `battery()` returns the hub voltage, or None.
- `is_connected()` wraps `hub.connection.is_alive()`.

### Windows readiness (no hardware)

- Smoke test in CI: `boost-console --help` and the parser tests run on `windows-latest`.
- Console output is kept ASCII-safe (Windows code pages). This is checked in a test, or by ruff/grep in CI.
- Verify that Ctrl+C on Windows stops motors via the fake hub path (signal in main thread, worker
  daemon thread).
- `docs/setup-windows.md`: Thonny setup (Tools → Options → Interpreter → `.venv\Scripts\python.exe`)
  and VS Code. Add a `boost-console` section and a checklist for the #4 session, in order.
- Double-click launchers in `windows/`: `console.cmd` (runs `uv run boost-console`, then `pause`)
  so kids don't need a terminal.

### BOOSTreveng

These are protocol notes with Linux-only gatttool scripts, not a library. pylgbst already covers
everything in them. They are used only as reference, linked in `docs/hardware-notes.md` next to
LEGO's official wireless protocol spec.

## Open / left to the builder

- Exact raw command syntax details and help texts (keep them short).
- The fuzzy-match threshold for "did you mean".
- Whether the bottom bar refreshes from sensor subscriptions or only after each command (start with
  "after each command"; it is cheaper and simpler).
- German aliases wait for decision #7.

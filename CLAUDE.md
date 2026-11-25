# hubbit — guide for Claude Code

Python experiments controlling a **LEGO BOOST Move Hub (17101 / 88006)** over Bluetooth LE
with [pylgbst](https://github.com/undera/pylgbst), without the LEGO app. Used on macOS
(primary), Linux (Kali, Raspberry Pi OS, Ubuntu) and Windows (a kids notebook).

## Commands

```bash
uv sync                          # create/update .venv (Python 3.12 pinned in .python-version)
uv run hubbit-scan               # find hubs, print addresses (needs hub switched on)
uv run hubbit-console            # interactive console (--simulate: no hub needed)
uv run hubbit-tui                # full-screen button window (textual), same session core
uv run experiments/02_hub_info.py
uv run kids/01_hello_light.py
uv run pytest                    # unit tests — no hardware needed
uv run ruff check . && uv run ruff format .
```

Always use `uv run` / `uv add`; never `pip install` into the venv by hand.

## Layout

- `src/hubbit/` — small helper package
  - `scan.py`: own BLE scan **with timeout** (pylgbst's discovery blocks forever); a known
    address is waited for with it too. `hubbit-scan --save` writes the address into `.env`
  - `config.py`: per-machine `.env` (BOOST_HUB_ADDRESS, BOOST_LANG, BOOST_TRIM; shell variables win).
    Claude cannot read `.env*` (sandbox/permission deny) - ask the user what is in it
  - `hub.py`: `connect()`, `boost()` context manager, `safe_shutdown()` (stops motors, times out)
  - `kid.py`: `Robot` — simplified API for the kids track (colors by name, speeds in %)
  - `commands.py`: text command parser for the console (aliases, limits, help) — pure logic
  - `session.py`: long-running console session — worker thread, `stop`, watchdog, reconnect.
    **Only the worker thread talks to the hub** (pylgbst allows one pending request).
  - `console.py`: `hubbit-console` (prompt_toolkit; plain line mode when stdin is not a TTY)
  - `tui.py`: `hubbit-tui` (textual). Buttons/keys/command line all go through
    `Session.handle`; tested headless with textual's `Pilot` (`tests/test_tui.py`)
    Live sensor panel = `Session(poll=...)`: the idle worker refreshes cached readings
    (battery only every 30 s); polls are never queued, so they never delay a command
  - `sim.py`: pretend hub for `--simulate` and CI smoke tests
  - `i18n.py`: English/German message tables, German colour words, umlaut normalising.
    German words are always accepted; `lang` only picks the output language
- `experiments/NN_name.py` — numbered adult experiments, one topic each
- `kids/NN_name.py` — "missions" for a young programmer (see rules below);
  German copies in `kids/de/` using `Roboter` (German method names)
- `tests/` — unit tests with fake hubs; CI runs them on macOS, Ubuntu, Windows
- `windows/` — `.cmd` double-click launchers (CRLF via `.gitattributes`); one per kids mission
- `docs/` — per-OS setup, hardware notes, troubleshooting, workflow

## Rules

- **Hardware safety:** every script that touches the hub uses `with boost() as hub:` or
  `with Robot() as robot:` so motors stop on errors/Ctrl+C. Default motor speeds ≤ 50%.
  Mark scripts that move with a `SAFETY` line in the docstring.
- **Claude cannot see or press the hub.** Before running a hardware script, ask the user to
  switch on the hub (green button). If a scan finds nothing, ask — don't retry in a loop.
- **pylgbst is pinned to a git commit** (see `[tool.uv.sources]` in `pyproject.toml`):
  PyPI 1.3.0 uses `bleak.discover()`, removed in bleak ≥ 1.0. Don't switch back to PyPI
  until a new release exists. Read the installed source in
  `.venv/lib/python3.12/site-packages/pylgbst/` rather than guessing its API.
- **Cross-platform:** no OS-specific paths/shell tricks in Python code; keep bleak as the
  only backend unless an issue says otherwise. Hub address = MAC on Linux/Windows,
  CoreBluetooth UUID on macOS (`BOOST_HUB_ADDRESS` env var).
- **No real hub addresses** (MAC / CoreBluetooth UUID) in committed files, issues or PRs:
  write `00:16:53:XX:XX:XX`. They identify a device in the user's home.
- **Printed text is ASCII-only** (Windows code pages); `tests/test_portability.py` checks it.
- **Kids track:** short scripts (< 30 lines), only `hubbit.kid.Robot`, a comment header
  with "Mission", "How to run", "Try this" (German: `Roboter`, "So startest du",
  "Probier mal"; new or changed missions go into both languages, each with a launcher). No advanced Python (no lambdas, classes, async).
- New experiment: next free number, docstring with purpose / run command / hardware needs.
  Add a unit test when you add logic to `src/hubbit/`.

## Sandbox and permissions

`.claude/settings.json` allows the usual uv/git/gh PR commands, asks before `gh api` and
label/repo changes, and denies force pushes and pushes to `main`. In the sandbox:
`gh` and the hardware commands (`hubbit-scan`, `hubbit-console`, `hubbit-tui`, `experiments/`,
`kids/`) run
outside it (`excludedCommands`: gh fails TLS checks inside, Bluetooth is unavailable inside);
PyPI and GitHub hosts are allowed. An exclusion only applies when **every** part of a command
matches: run `gh ...` on its own, without `cd ... &&`, pipes or redirects. Push branches with
`git push origin <branch>` (no `-u`: the sandbox write-protects `.git/config`).

## Workflow

**Start every session with the pinned Roadmap issue** (`gh issue view 8`). It has the
next step, the batch plan with usage estimates/actuals, the cut lines and open decisions.
At the end of a batch: ask the user for `/usage` numbers, record them in #8, and update
"Next step" there.

Work is tracked in GitHub issues (`gh issue list`). Record hardware findings (what worked on
which OS) in `docs/hardware-notes.md`. Run `uv run ruff check . && uv run pytest` before committing.

**`main` is protected — never commit or push to it directly.** For each issue: branch
`NN-short-name` → commit (`Closes #N`) → push → `gh pr create` with a **Conventional Commits
PR title** (`feat(tui): ...`, `fix(hub): ...`; required check, see `docs/releasing.md`). Wait for CI on all three OSes;
when green, Claude merges its own PR (`gh pr merge --squash --delete-branch --admin`) and tells
the user. Outside PRs: review only, never merge them without the user's go-ahead.
New issues are triaged per `docs/triage.md` (labels: one type + area, remove `needs-triage`).

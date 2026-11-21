# lego-boost — guide for Claude Code

Python experiments controlling a **LEGO BOOST Move Hub (17101 / 88006)** over Bluetooth LE
with [pylgbst](https://github.com/undera/pylgbst), without the LEGO app. Used on macOS
(primary), Linux (Kali, Raspberry Pi OS, Ubuntu) and Windows (a child's notebook).

## Commands

```bash
uv sync                          # create/update .venv (Python 3.12 pinned in .python-version)
uv run boost-scan                # find hubs, print addresses (needs hub switched on)
uv run experiments/02_hub_info.py
uv run kids/01_hello_light.py
uv run pytest                    # unit tests — no hardware needed
uv run ruff check . && uv run ruff format .
```

Always use `uv run` / `uv add`; never `pip install` into the venv by hand.

## Layout

- `src/lego_boost/` — small helper package
  - `scan.py`: own BLE scan **with timeout** (pylgbst's discovery blocks forever)
  - `hub.py`: `connect()`, `boost()` context manager, `safe_shutdown()` (stops motors, times out)
  - `kid.py`: `Robot` — simplified API for the kids track (colors by name, speeds in %)
- `experiments/NN_name.py` — numbered adult experiments, one topic each
- `kids/NN_name.py` — "missions" for a young programmer (see rules below)
- `tests/` — unit tests with fake hubs; CI runs them on macOS, Ubuntu, Windows
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
- **Kids track:** short scripts (< 30 lines), only `lego_boost.kid.Robot`, a comment header
  with "Mission", "How to run", "Try this". No advanced Python (no lambdas, classes, async).
- New experiment: next free number, docstring with purpose / run command / hardware needs.
  Add a unit test when you add logic to `src/lego_boost/`.

## Workflow

Work is tracked in GitHub issues (`gh issue list`). Reference the issue in commits
(`Closes #N`). Record hardware findings (what worked on which OS) in `docs/hardware-notes.md`.
Run `uv run ruff check . && uv run pytest` before committing.

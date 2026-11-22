# Contributing

Thanks for your interest! This is a small hobby project: Python experiments with the
LEGO BOOST Move Hub, plus a kids track. Contributions are welcome. Please read this first.

## Ways to contribute

- **Report a bug or a hardware result.** Use the [issue forms](../../issues/new/choose).
  Reports that a setup works (or doesn't) on your OS / Bluetooth adapter are very useful.
- **Ask a question or share an idea** in [Discussions](../../discussions), not in issues.
- **Send a pull request.** For anything bigger than a typo, open (or comment on) an issue
  first so we can agree on the approach. Issues labelled `good first issue` or `help wanted`
  are a good start.

## Development setup

```bash
uv sync                                   # Python 3.12 + dependencies into .venv
uv run pytest                             # unit tests, no hardware needed
uv run ruff check . && uv run ruff format .
```

Per-OS Bluetooth notes: [macOS](docs/setup-macos.md) · [Linux](docs/setup-linux.md) ·
[Windows](docs/setup-windows.md). Use `uv run` / `uv add`, never `pip install` into the venv.

## Rules for code

- **Hardware safety:** every script that touches the hub uses `with boost() as hub:` or
  `with Robot() as robot:` so motors stop on errors and Ctrl+C. Default motor speeds ≤ 50 %.
  Scripts that make the model move have a `SAFETY` line in their docstring.
- **Cross-platform:** the same code must run on macOS, Linux and Windows. bleak is the only
  Bluetooth backend; no OS-specific paths or shell tricks in Python code.
- **Printed text is ASCII-only** (old Windows consoles); `tests/test_portability.py` checks it.
- **Kids track** (`kids/`): short scripts (< 30 lines), only `lego_boost.kid.Robot`, a comment
  header with "Mission", "How to run", "Try this", and no advanced Python (no classes, lambdas,
  async).
- New logic in `src/lego_boost/` comes with a unit test (fake hubs, see `tests/`).
- GitHub Actions are pinned to commit SHAs (with the version as a comment); Dependabot
  updates them. Please keep new actions pinned the same way.
- pylgbst is pinned to a git commit on purpose (see `pyproject.toml`). Please don't change it
  in an unrelated PR.

## Pull requests

1. Fork, create a branch (`NN-short-name`, with `NN` = issue number).
2. Keep the PR focused on one thing; reference the issue (`Closes #NN`).
3. Run `uv run ruff check . && uv run ruff format --check . && uv run pytest` locally.
4. CI must pass on macOS, Ubuntu and Windows. For first-time contributors, the maintainer
   has to approve the CI run first, so don't worry if it waits.
5. If you changed something hardware-related, say what you tested on which hub and OS.
   Untested on hardware is fine, just say so.

PRs are squash-merged into `main`; nobody pushes to `main` directly.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be kind, especially
since some of the users here are kids.

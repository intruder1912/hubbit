---
description: Scaffold the next numbered experiment (or kids mission with --kids)
argument-hint: <topic> [--kids]
---

Create a new script for: $ARGUMENTS

1. If `--kids` is given, target `kids/`, otherwise `experiments/`. Find the next free
   two-digit number `NN` there.
2. Read CLAUDE.md rules (hardware safety, kids-track style) and one existing script in the
   same folder as a style reference. Check the pylgbst source in `.venv` for any API you use.
3. Write `NN_<snake_topic>.py`:
   - experiments: docstring with purpose, `Run:` line, `Hardware:` line (+ `SAFETY` if it
     moves), use `with boost() as hub:`.
   - kids: header comments "Mission", "How to run", "Try this"; only `Robot`; < 30 lines.
4. Run `uv run ruff check --fix <file> && uv run ruff format <file>`.
5. Don't run it on hardware yourself — ask the user to switch the hub on first.
6. Offer to create/link a GitHub issue if none exists.

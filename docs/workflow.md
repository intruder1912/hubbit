# Workflow

- **Everything is a GitHub issue.** Labels: `experiment`, `kids`, `platform:macos`,
  `platform:linux`, `platform:windows`, `bug`, `docs`, `infra`.
- Small changes go straight to `main`; bigger ones on a branch `NN-short-name` + PR.
- Commit messages reference issues: `Add tilt experiment (closes #7)`.
- Hardware results (what worked, on which OS) → `docs/hardware-notes.md` platform log.
- With Claude Code: `/new-experiment <topic>` scaffolds the next numbered script.
  `gh issue list` / `gh issue view N` give Claude the task context.
- Before committing: `uv run ruff check . && uv run ruff format . && uv run pytest`.
- CI (GitHub Actions) runs lint + tests on macOS, Ubuntu and Windows for every push/PR.

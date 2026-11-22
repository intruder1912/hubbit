# Workflow

- **Everything is a GitHub issue.** Labels and triage: see [triage.md](triage.md).
- **`main` is protected.** Every change goes through a pull request from a branch
  `NN-short-name` (`NN` = issue number). CI must pass on macOS, Ubuntu and Windows, and the
  branch must be up to date. PRs are squash-merged; branches are deleted after merge.
  - Outside contributors: fork + PR, needs the maintainer's approval (CODEOWNERS).
  - Maintainer (and Claude Code in the maintainer's sessions): same PR flow, may merge without
    a second reviewer once CI is green (ruleset bypass, PR-only).
- Commit messages / PR descriptions reference issues: `Add tilt experiment (closes #7)`.
- Hardware results (what worked, on which OS) → `docs/hardware-notes.md` platform log.
- With Claude Code: `/new-experiment <topic>` scaffolds the next numbered script.
  `gh issue list` / `gh issue view N` give Claude the task context.
- Before pushing: `uv run ruff check . && uv run ruff format . && uv run pytest`.
- Dependabot opens grouped update PRs monthly (GitHub Actions, Python packages); security
  updates arrive as soon as an advisory exists.

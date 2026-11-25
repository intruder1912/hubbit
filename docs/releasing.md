# Releasing

Versions follow [Semantic Versioning](https://semver.org/). While we are at 0.x, a minor
bump (0.1 → 0.2) may change things; a patch (0.1.0 → 0.1.1) only fixes. The version lives
only in `pyproject.toml`.

## Commit messages

We squash-merge, so the **PR title** is the commit on `main`. It must follow
[Conventional Commits](https://www.conventionalcommits.org/) (checked by the `PR title`
workflow, a required check):

```
feat(console): add a "dance" command
fix(hub): retry once after a fast connect failure
docs: Kali reset steps
chore(deps): bump the python group
```

Types: `feat` (→ minor bump), `fix` / `perf` (→ patch), `docs`, `test`, `refactor`,
`build`, `ci`, `chore`, `revert`. A `!` after the type (`feat!:`) marks a breaking change.
Scopes are optional: `hub`, `kid`, `console`, `tui`, `scan`, `kids`, `windows`, `docs`, `deps`, ...

## Making a release

1. Branch `release-vX.Y.Z` from an up-to-date `main`.
2. Bump the version: `uv version --bump minor` (or `patch`), then `uv lock`.
3. Changelog: `uvx git-cliff --unreleased --tag vX.Y.Z --prepend CHANGELOG.md`, then
   edit the new section by hand if needed (it becomes the release notes).
4. PR titled `chore(release): vX.Y.Z`; merge when CI is green.
5. Tag the merge commit and push the tag (admins only, tag ruleset):
   ```bash
   git switch main && git pull
   git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z
   ```
6. The `Release` workflow checks that the tag matches `pyproject.toml`, runs the tests,
   builds sdist + wheel, attests their provenance and creates the GitHub Release with the
   changelog section as notes.

Check a downloaded file: `gh attestation verify hubbit-X.Y.Z-py3-none-any.whl --repo intruder1912/hubbit`.
Releases before the rename (v0.1.0, v0.1.1: files named `lego_boost-0.1.x-...`) were attested
as `intruder1912/lego-boost` and only verify with `--repo intruder1912/lego-boost`.

## Why not PyPI (yet)

PyPI rejects packages with direct git dependencies, and pylgbst is pinned to a git commit
until upstream releases (#6). Users install from a clone (`uv sync`), as the setup guides
describe. Once pylgbst is back on PyPI, a trusted-publishing step can be added here.

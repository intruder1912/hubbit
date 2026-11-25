# Issue triage

New issues from the issue forms arrive with `needs-triage` (and a `platform:*` label, added
automatically from the form). Triage = look at the
[`needs-triage` list](https://github.com/intruder1912/hubbit/issues?q=is%3Aopen+label%3Aneeds-triage)
and, for each issue, do one of the following:

| Situation | Do this |
|---|---|
| Clear and actionable | Set **one type** + **area** labels, remove `needs-triage`. Optionally `good first issue` / `help wanted`. |
| Missing details | Ask in a comment, replace `needs-triage` with `needs-info`. When the author replies, a workflow moves it back to `needs-triage`; after 21 days without reply it's closed automatically. |
| Question, not a task | Convert to a Discussion (issue sidebar → "Convert to discussion"). |
| Duplicate | Comment "Duplicate of #N", label `duplicate`, close. |
| Out of scope / won't do | Explain briefly, label `wontfix` or `invalid`, close. |
| Security problem posted publicly | Ask the reporter to use private reporting (SECURITY.md); hide or delete details if needed. |

## Labels

| Group | Labels | Meaning |
|---|---|---|
| Type (one) | `bug`, `enhancement`, `documentation`, `question` | What kind of work it is |
| Area (any) | `kids`, `console`, `experiment`, `infra`, `hardware`, `dependencies` | Which part of the repo; `hardware` = needs the physical hub |
| Platform (any) | `platform:macos`, `platform:linux`, `platform:windows` | OS-specific |
| Status | `needs-triage`, `needs-info`, `blocked`, `stale` | Where it stands; `stale` is set by the bot |
| Contributors | `good first issue`, `help wanted` | Good entry points for others |
| Resolution | `duplicate`, `invalid`, `wontfix` | Why it was closed without a change |
| Planning | `roadmap` | The pinned roadmap issue only |

Pull requests from outside contributors: check that CI may run (first runs need approval in
the PR), review against [CONTRIBUTING.md](../CONTRIBUTING.md), squash-merge.

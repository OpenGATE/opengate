# Found bugs (agent-maintained log)

Every bug an agent notices but does **not** fix in the same change must be logged here
immediately. Do not silently work around a defect: log it, then decide with the user
whether to fix it now.

This log is for *newly discovered* defects. Things already tracked upstream belong in
GitHub issues — link them, do not duplicate their content.

---

## Entry template

```markdown
### B-NNN — <one-line summary>
- **Status**: open | confirmed | workaround | fixing | fixed (commit) | wontfix
- **Severity**: blocker | high | medium | low
- **Area**: e.g. `opengate/actors/doseactors.py`, `core/…`, `.github/workflows/…`
- **Symptom**: what the user/agent sees (exact error message).
- **Reproduce**: exact commands, minimal snippet, seeds.
- **Environment**: commit hash, OS, Python, Geant4/ITK versions, dev env or wheel.
- **Suspected cause**: hypothesis, with the file:line you inspected.
- **Workaround**: what to do meanwhile, if anything.
- **Related**: task ids in `task-list.md`, GitHub issue/PR links.
```

Include enough to reproduce without rediscovering the environment. Never paste long logs
inline — quote the first error line and the failing assertion.

---

## Open

| id | severity | area | summary | status | related |
| --- | --- | --- | --- | --- | --- |
| — | — | — | *(no bugs logged yet — add the first one as you find it)* | — | — |

---

## Entries

<!-- Append new entries below, newest last. Keep the template headings so entries stay greppable. -->

---

## Closed

| id | summary | resolution | commit |
| --- | --- | --- | --- |
| — | — | — | — |

---

## Common false positives (check before logging)

Distinguish these from real bugs; they waste the most time:

| Symptom | Likely cause | Check |
| --- | --- | --- |
| Import error for `opengate_core` | wrong venv / missing local build | `skills/environment-setup` §7 |
| Many tests failing on missing input files | `opengate/tests/data` submodule not initialized | `ls opengate/tests/data` |
| Import error for `torch` / `gaga_phsp` / `pytomography` | optional extras not installed | `skills/environment-setup` §5 |
| `cannot allocate memory in static TLS block` | Geant4 TLS model | `skills/environment-setup` §4.5 |
| Test passes alone, fails in the suite | resource contention (`-n all`) or test interdependence | rerun with `-p sp -n 1`, then with `-f` |
| Stochastic assertion failing at low statistics | test design, not code | inspect the tolerance, not the simulation |
| Behaviour differs from the docs | docs may lag the code | hierarchy of truth in `AGENTS.md` §5 |
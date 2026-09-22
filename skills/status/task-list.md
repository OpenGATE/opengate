# Task list (agent-maintained)

Shared work list for agents and humans on this repository. **Update it in the same turn
you start or finish work** — an agent that plans work here but does not mark it done makes
the next agent repeat it.

Rules:

- One line per task, with a stable id (`T-001`, `T-002`, …).
- Status is one of: `todo`, `doing`, `blocked`, `done`, `dropped`.
- Always name the files/areas touched, so the next reader can find the change.
- When a task reveals a bug you are not fixing now, add it to
  [`found-bugs.md`](found-bugs.md) and link the bug id here.
- Keep `done` tasks for one release cycle, then move them to the archive at the bottom.

Columns: **id · status · area · task · evidence**.

---

## Active

| id | status | area | task | evidence |
| --- | --- | --- | --- | --- |
| T-001 | done | `AGENTS.md`, `skills/` | Add agent entry point + skills for environment setup, tests, build/CI, code style, architecture, docs, and a status folder. | Files added on branch `agentic-skills`; see this directory. |
| T-005 | done | `skills/*` | First trial of the skills against a real environment: import check, smoke test, 30-test slice. | `opengate_tests -i 1 -e 12 -n 4` → `Summary pass: 30/30`, `True`, 2.2 min; `-t actors/test008_dose_actor.py` → `1/1`, `True`. Paths came from `user_secrets.json`, not hard-coded. |
| T-006 | done | `skills/environment-setup`, `skills/running-tests`, `AGENTS.md` | Fix defects the trial exposed: wrong `-t` example path, missing venv-activation requirement, `pip` vs `uv` on uv-made venvs, stale-`.so` rebuild procedure. | Same commit; each correction cites the observed failure. |
| T-010 | done | `skills/*`, `AGENTS.md`, `.gitignore` | Move all machine-specific paths into a git-ignored `user_secrets.json` at the repo root; make every skill command read from it instead of hard-coding paths. | `git check-ignore -v user_secrets.json` → `.gitignore:88`; no absolute dev path remains in `AGENTS.md` or `skills/*`. |
| T-002 | todo | `skills/` | Keep skills in sync with the code: any PR that changes test runner options, CI keys, or the object lifecycle must update the matching `SKILL.md`. | Proven necessary by T-006 — the trial found 3 wrong instructions. |
| T-003 | todo | `skills/environment-setup` | Verify the *full* source-build path (§4.1–4.4) end to end, not just the reuse of an existing build tree as in T-005. | Only the rebuild against pre-existing Geant4/ITK builds was exercised. |
| T-004 | todo | ops | Decide how generated session logs (`opengate/tests/log/`, `output_dashboard/`) are shared between agents without being committed. | — |
| T-007 | todo | `opengate/bin/opengate_tests_helpers.py` | The runner hardcodes `python <test>` instead of `sys.executable`, so an un-activated venv fails every test opaquely. Consider using `sys.executable` (a `FIXME` already exists at line ~341). | See B-002. Needs a Windows-safe quoting approach per that comment. |
| T-008 | todo | `opengate/bin/opengate_tests_helpers.py` | `check_environment()` does not detect a stale `opengate_core`; the suite reports 458 tests discovered and then every one fails. A version/`hasattr` preflight would fail fast. | See B-001. |

## Blocked

| id | status | area | task | blocker |
| --- | --- | --- | --- | --- |
| T-011 | todo | `skills/*`, `AGENTS.md` | Verify no absolute dev-machine path survives in any committed file. A grep for the local root is the acceptance test. | Run: `grep -rn "/Data/\|/home/" AGENTS.md skills/` — must return only placeholders. |
| T-009 | blocked | tests | Run the optional-dependency tests (torch / gaga_phsp / pytomography). 90 of 458 files are ignored, plus 11 more for missing `torch`. | Those extras are not installed in the user's designated environment. |

## Archive (completed)

| id | status | area | task | evidence |
| --- | --- | --- | --- | --- |
| — | — | — | *(nothing archived yet)* | — |

---

## How to use this file without creating noise

1. Before starting work: search this file for the area you are touching. If a task
   exists, switch it to `doing` and add your name/agent id.
2. Do not create a task for a one-line fix that you complete immediately — such work is
   visible in git history.
3. `evidence` is mandatory for `done`: the command you ran, the commit hash, or the file
   you changed. "Looks fine" is not evidence.
4. If you drop a task, say **why** in the task line rather than deleting it silently.
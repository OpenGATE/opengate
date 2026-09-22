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
| T-011 | todo | `skills/*`, `AGENTS.md` | Verify no absolute dev-machine path survives in any committed file. | `grep -rn "/Data/\|/home/" AGENTS.md skills/` must return only placeholders. |
| T-013 | todo | `opengate/bin/opengate_tests_helpers.py` | `get_required_g4_version()` indexes the non-existent `jobs.build_wheel` and silently falls back to a literal; read the workflow-level `env.GEANT4_VERSION` instead. | See B-005. |
| T-014 | done | tests | Re-run the two baseline failures on the corrected environment and confirm whether they are genuine repository bugs. | **`geometry/test102_gammex467.py` OK (18.1 s)** and **`geometry/test107_macaco1_mt.py` OK (60.6 s)** → `Summary pass: 2/2`, `True`; logs end with “Great, tests are ok.” **No repository bug** — the failures came from a stale `opengate/tests/data` submodule checkout (T-020). |
| T-020 | done | submodule / tests | Fix the `opengate/tests/data` checkout, which lagged the pointer recorded in the parent repo by four commits, so the reference data for test102/test107 was absent. | `git submodule update --init opengate/tests/data` → HEAD `9fabbdddf`; `output_ref/test102_gammex467/` and `output_ref/test107_macaco1/` now populated. See B-008. |
| T-021 | todo | `opengate/tests/utility.py` | `create_output_ref()` calls `mkdir(..., exist_ok=True)`, so a missing reference dataset produces an *empty directory* instead of a clear “reference data missing” error — the test then fails deep inside the comparison. Consider asserting the expected files exist. | See B-008. |
| T-019 | todo | `core/setup.py` | Consider mirroring the parallelism fix into a documented env var for CI, and check whether `core/config.json` should be auto-created from `CMAKE_PREFIX_PATH` so the Geant4/ITK wiring is explicit. | See `skills/environment-setup` §4.3 and B-007. |
| T-015 | todo | tests / `.gitignore` | A full-suite run leaves an untracked `simulation.json` in the repo root; make the test write to an ignored path or add an ignore rule. | See B-006. |
| T-016 | done | `AGENTS.md` | Encode the git safety rules: `master` is read-only for agents (sync only), every change on a fresh branch cut from the up-to-date local `master`, never commit without user approval. | `AGENTS.md` golden rules 1–2 and new §6 (sync, branch creation, rebase policy). |
| T-017 | done | environment | Relink `opengate_core` against the rebuilt Geant4 v11.4.2 so the suite is CI-comparable. | Relink via `uv pip` succeeded; runner now prints `Geant4 version is OK`. First attempt failed (`python -m pip` on a `uv` venv). |
| T-018 | done | `core/setup.py` | Remove the hardcoded `-j4` / `--parallel 4` and default to all cores, with an `OPEN_GATE_BUILD_JOBS` override. | See B-007. |

## Blocked

| id | status | area | task | blocker |
| --- | --- | --- | --- | --- |
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
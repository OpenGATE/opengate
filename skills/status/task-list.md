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
| T-029 | todo | `opengate/bin/opengate_tests_helpers.py` | **Apply the two verified runner patches** that stage scoping left uncommitted: B-005 (read `env.GEANT4_VERSION` from the workflow level; also guard `tests_dir.parents[2]` against `IndexError`) and B-002 (launch tests with `sys.executable` via `subprocess.run([...], shell=False)`). | Both patches were written and **proved at runtime** this session, then reverted because only `skills/`/`AGENTS.md` were in scope. Repro + proof recorded in `found-bugs.md` B-002/B-005. |
| T-003 | todo | `skills/environment-setup` | Verify the *full* source-build path (§4.1–4.4) end to end, not just the reuse of an existing build tree as in T-005. | Only the rebuild against pre-existing Geant4/ITK builds was exercised. |
| T-004 | todo | ops | Decide how generated session logs (`opengate/tests/log/`, `output_dashboard/`) are shared between agents without being committed. | — |
| T-007 | todo | `opengate/bin/opengate_tests_helpers.py` | The runner hardcodes `python <test>` instead of `sys.executable`, so an un-activated venv fails every test opaquely. Consider using `sys.executable` (a `FIXME` already exists at line ~341). | See B-002. Needs a Windows-safe quoting approach per that comment. |
| T-008 | todo | `opengate/bin/opengate_tests_helpers.py` | `check_environment()` does not detect a stale `opengate_core`; the suite reports 458 tests discovered and then every one fails. A version/`hasattr` preflight would fail fast. | See B-001. |
| T-011 | done | `skills/*`, `AGENTS.md` | Verify no absolute dev-machine path survives in any committed file. | **Verified clean.** `grep -rnE '/Users/[a-zA-Z]\|/home/[a-zA-Z]\|/Data/\|C:\\\\Users' AGENTS.md skills/` returns only the audit instruction itself (`task-list.md`). All remaining paths are placeholders (`/absolute/…`, `<prefix>`, `<machine>`); machine values live in the git-ignored `user_secrets.json`. |
| T-013 | todo | `opengate/bin/opengate_tests_helpers.py` | `get_required_g4_version()` indexes the non-existent `jobs.build_wheel` and silently falls back to a literal; read the workflow-level `env.GEANT4_VERSION` instead. | See B-005. |
| T-014 | done | tests | Re-run the two baseline failures on the corrected environment and confirm whether they are genuine repository bugs. | **`geometry/test102_gammex467.py` OK (18.1 s)** and **`geometry/test107_macaco1_mt.py` OK (60.6 s)** → `Summary pass: 2/2`, `True`; logs end with “Great, tests are ok.” **No repository bug** — the failures came from a stale `opengate/tests/data` submodule checkout (T-020). |
| T-020 | done | submodule / tests | Fix the `opengate/tests/data` checkout, which lagged the pointer recorded in the parent repo by four commits, so the reference data for test102/test107 was absent. | `git submodule update --init opengate/tests/data` → HEAD `9fabbdddf`; `output_ref/test102_gammex467/` and `output_ref/test107_macaco1/` now populated. See B-008. |
| T-021 | todo | `opengate/tests/utility.py` | `create_output_ref()` calls `mkdir(..., exist_ok=True)`, so a missing reference dataset produces an *empty directory* instead of a clear “reference data missing” error — the test then fails deep inside the comparison. Consider asserting the expected files exist. | See B-008. |
| T-019 | todo | `core/setup.py` | Consider mirroring the parallelism fix into a documented env var for CI, and check whether `core/config.json` should be auto-created from `CMAKE_PREFIX_PATH` so the Geant4/ITK wiring is explicit. | See `skills/environment-setup` §4.3 and B-007. |
| T-015 | todo | tests / `.gitignore` | A full-suite run leaves an untracked `simulation.json` in the repo root; make the test write to an ignored path or add an ignore rule. | See B-006. |
| T-016 | done | `AGENTS.md` | Encode the git safety rules: `master` is read-only for agents (sync only), every change on a fresh branch cut from the up-to-date local `master`, never commit without user approval. | `AGENTS.md` golden rules 1–2 and new §6 (sync, branch creation, rebase policy). |
| T-017 | done | environment | Relink `opengate_core` against the rebuilt Geant4 v11.4.2 so the suite is CI-comparable. | Relink via `uv pip` succeeded; runner now prints `Geant4 version is OK`. First attempt failed (`python -m pip` on a `uv` venv). |
| T-018 | done | `core/setup.py` | Remove the hardcoded `-j4` / `--parallel 4` and default to all cores, with an `OPEN_GATE_BUILD_JOBS` override. | See B-007. |
| T-022 | done | `skills/README.md`, `skills/engineering/` | Add a skills README (map of the directory, role-vs-task split, conventions, how to add a skill) and four role-based engineering skills: `python-gate-developer.md`, `geant4-physics-expert.md`, `simulation-debugger.md`, `test-writer.md`. | `skills/README.md` added; `skills/engineering/` created; both listed in the `AGENTS.md` skills index and the `project-status.md` asset table. |
| T-023 | done | `skills/engineering/` | Add the missing role skills: `gate-physics-expert.md` (GATE physics layer — physics manager, **sources**, **actors**, filters, biasing, normalisation), `geant4-geometry-expert.md` (raw G4 geometry — solids, volumes, navigation, overlaps, C++ bindings) and `gate-geometry-expert.md` (GATE geometry layer — volume tree, solids, materials, placement/repetition, regions, fields). | Three new files in `skills/engineering/`; each grounded in real class names (`SolidBase`/`BoxSolid`…, `GenericSource`, `DoseActor`, `reference_physics_list_*`); listed in `skills/README.md`, the `AGENTS.md` skills index and the `project-status.md` asset table. |
| T-024 | done | `skills/engineering/SKILL.md` | Add the role-skill index so the `engineering/` directory follows the `<topic>/SKILL.md` convention and its roles are discoverable from the top-level indexes. | `skills/engineering/SKILL.md` added (role table, the two layered pairs, role composition, conventions, how-to-add); linked from `skills/README.md` (layout tree + "which skill" table + role section), `AGENTS.md` skills index and `project-status.md`. |
| T-025 | done | environment | Verify the dev environment end to end after the Geant4 11.4.2 relink: 30-test slice. | `opengate_tests -i 1 -e 12 -n 4` → `Summary pass: 30/30`, `Geant4 version is OK`, `True`, 5.9 min (log kept outside the repo, under `$OPEN_GATE_ENV`). Both packages at 10.1.1 == `VERSION`; no untracked pollution in the repo root. |
| T-027 | done | `skills/` | De-duplicate the four skills whose titles look overlapping (`environment-setup`/`build-and-ci`, `code-style`/`architecture`) by giving each fact a single owner and replacing copies with cross-references; document the boundary rules in `skills/README.md`. | `environment-setup` §6 (CI recipe, ~20 lines) reduced to a pointer at `build-and-ci` §5 — `grep -c 'python -m build'` now returns 1, not 2. `build-and-ci` §6 reframed as *packaging consequences only*, pointing at `environment-setup` §4.3. Corrected `build-and-ci` §4 `-r` wording to match the real help text (`Start the last 10 tests and 1/4 of the others randomly`, `opengate/bin/opengate_tests.py:41`). Added an "Easily-confused pairs — one owner per fact" table to `skills/README.md` and a boundary note in `AGENTS.md` §3. All links resolve; pre-commit clean. |
| T-028 | done | `skills/environment-setup/`, `skills/build-and-ci/` (removed) | Merge `build-and-ci` into `environment-setup` §6 and delete the separate directory — the two overlapped in their CI-recipe text and a single "build & environment" skill is easier to keep truthful. Repointed every reference. | `skills/build-and-ci/` removed; `environment-setup` §6 rewritten as *Build, packaging and CI* with subsections 6.1 topology, 6.2 release, 6.3 what CI tests, 6.4 reproduce locally, 6.5 `core/` packaging consequences, 6.6 safe workflow edits. Header of `environment-setup` now states the two-part scope. References updated in `AGENTS.md` §3, `skills/README.md` (tree, which-skill table, boundary table), `skills/engineering/SKILL.md`, `skills/status/project-status.md`. Two relative links corrected for the new directory depth (`../engineering/…`, `../running-tests/…`). Link check over the whole tree: 0 broken. |
| T-026 | done | `skills/build-and-ci/SKILL.md`, `.gitignore` | Solve B-010 by writing the missing build/CI skill instead of dropping the index rows, and fix the hidden cause found while doing it (B-011: `.gitignore`'s `build*/` made the directory un-committable). | All 7 job names grepped and confirmed in `.github/workflows/main.yml`; `setup.py:15` pin, `core/setup.py:30` `VERSION` read, cron `0 0 * * 0,3`, `paths-ignore: docs/**` and tag-only publish each verified. `!skills/build*-*/` added to `.gitignore`: skill now appears in `git status`, while `build/`, `core/build/`, `dist/`, `*.whl` stay ignored. B-010 and B-011 moved to **Closed**. |
| T-030 | done | `skills/engineering/` | Add the missing `gate-chemistry-expert.md` role skill: the GATE chemistry layer (Geant4-DNA chemistry lists, chemistry world and scavengers, track-structure EM regions, chemistry actors and counters), including the alpha-stage warning. | New file `skills/engineering/gate-chemistry-expert.md`, grounded in real names from the code (`ChemistryManager`, `ChemistryList`, `ChemistryWorld`, `ChemicalCountingActor`, `chemistry_counter_types`, `known_g4_chemistry_list_names`, `set_track_structure_em_physics`); `H2O`-not-a-product, integer-`pH`, single-molecule-counter and manager-policy-conflict `fatal`s each cited from the source. Listed in `skills/README.md` (tree + which-skill + role tables), `skills/engineering/SKILL.md` (tables + worked example), the `AGENTS.md` skills index and `project-status.md`. |
| T-031 | done | `skills/environment-setup/` | Apply the "SKILL.md is an index" rule: `environment-setup/SKILL.md` was 862 lines (6× every other skill) and violated it. Extract its two deep topics to dedicated files — `geant4-itk.md` (Geant4/ITK/`opengate_core` compilation) and `build-and-ci.md` (packaging/release/CI) — leaving `SKILL.md` as an index with pointer stubs at §4 and §6. | `SKILL.md` 862 → 502 lines; new `geant4-itk.md` (280) and `build-and-ci.md` (188). Section numbering re-verified contiguous §0–§9; every moved-section ref repointed (`§4.6` → `geant4-itk.md` §7, `§4.5` → §6, `§4.3` → §4) across `AGENTS.md`, `skills/README.md`, `skills/engineering/{SKILL,gate-physics-expert,gate-geometry-expert,gate-chemistry-expert,geant4-geometry-expert,simulation-debugger,python-gate-developer,test-writer}.md` and `project-status.md`. Link scan over the whole tree + `AGENTS.md`: 0 broken. Convention added to `skills/README.md` §"Adding a new skill" (split past ~250 lines). |

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
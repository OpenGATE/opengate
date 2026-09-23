# Found bugs (agent-maintained log)

Every bug an agent notices but does **not** fix in the same change must be logged here
immediately. Do not silently work around a defect: log it, then decide with the user
whether to fix it now.

This log is for *newly discovered* defects. Things already tracked upstream belong in
GitHub issues — link them, do not duplicate their content.

## Two categories — do not confuse them

| Category | Meaning | Where it is fixed |
| --- | --- | --- |
| **Repository bug** | A defect in the code, tests, docs or CI of **this** project. | A commit in this repository. |
| **Environment issue** | The local machine's setup is wrong or outdated (Geant4/ITK version, stale compiled build, missing extras, wrong venv). **Nothing in the repo is broken.** | Fix the environment — see `skills/environment-setup`. Do **not** "fix" the repo for it. |

A failing or warning-laden run is **not** evidence of a repository bug until the environment
has been proven correct (see the checklist in `skills/environment-setup`). Most confusing
failures here are environment issues: a wrong Geant4 version, a stale compiled
`opengate_core`, an un-activated venv.

---

## Entry template

```markdown
### B-NNN — <one-line summary>
- **Status**: open | confirmed | workaround | fixing | fixed (commit) | wontfix
- **Category**: repository bug | environment issue
- **Severity**: blocker | high | medium | low
- **Area**: e.g. `opengate/actors/doseactors.py`, `core/…`, `.github/workflows/…`,
  or `<machine>/environment` for environment issues.
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

### Repository bugs

| id | severity | area | summary | status | related |
| --- | --- | --- |
| B-008 | low | `opengate/tests/utility.py` | `create_output_ref()` creates the reference directory with `exist_ok=True`, so when the test-data submodule is behind, the directory exists but is empty and the test fails with a misleading comparison error instead of “reference data missing”. | confirmed, open | T-021 |
| B-007 | medium | `core/setup.py` | The CMake build hardcoded a parallelism of **4** (`-j4` / `--parallel 4`), so a cold `opengate_core` build never used the machine's cores. | **fixed in this branch** | T-018 |
| B-002 | medium | `opengate/bin/opengate_tests_helpers.py` | The runner hardcodes `python <test>` instead of `sys.executable`, so an un-activated venv fails all tests with `ModuleNotFoundError: opengate`. | confirmed, open | T-007 |
| B-005 | low | `opengate/bin/opengate_tests_helpers.py` | `get_required_g4_version()` reads `jobs.build_wheel.env.GEANT4_VERSION`, a job that **does not exist**, so the required version silently falls back to a hard-coded `v11.4.2`. | confirmed, open | T-013 |
| B-006 | low | tests / `.gitignore` | A full-suite run leaves an untracked `simulation.json` in the repo root. | confirmed, open | T-015 |
| B-001 | medium | `opengate/bin/opengate_tests_helpers.py` | `check_environment()` does not detect a stale `opengate_core` nor a missing venv activation, so a broken environment looks like hundreds of failing tests. | open (UX gap) | T-008 |
| B-003 | low | `skills/` (our own docs) | The skills shipped a wrong `-t` example path, a `pip`-only install recipe for a `uv` venv, and omitted the activation requirement. | fixed in this branch | T-006 |
| B-010 | low | `skills/`, `AGENTS.md` | `AGENTS.md`, `skills/README.md` and `skills/status/project-status.md` all link to `skills/build-and-ci/SKILL.md`, a directory that **does not exist** in the tree — a dangling reference in the skills index. | **superseded by T-028** — the `build-and-ci` skill was merged into `environment-setup` §6 and the directory removed, so there is no longer a reference to fix | T-024, T-026, T-028 |
| B-011 | medium | `.gitignore` | `.gitignore:40` (`build*/`) also matches `skills/build-and-ci/`, so **any file in that directory is silently un-committable**. This is the hidden cause of B-010: the skill could be created locally but never entered git history. | **fixed in this branch** — added `!skills/build*-*/`; verified the skill is now tracked and that `build/`, `core/build/`, `dist/`, `*.whl` stay ignored | T-026 |

### Environment issues (not repository bugs)

| id | severity | area | summary | status | related |
| --- | --- | --- | --- | --- | --- |
| B-004 | high (for result validity) | local Geant4 build | The Geant4 checkout was at `v11.4.0` while the project pins `v11.4.2`, so the full-suite baseline was not CI-comparable. | **resolved** — Geant4 rebuilt at v11.4.2, `opengate_core` relinked; runner prints `Geant4 version is OK` | T-012, T-017 |
| B-009 | high (for result validity) | local `opengate/tests/data` submodule | The test-data submodule was checked out four commits behind the pointer recorded in the parent repo, so reference data for several tests was missing — producing the only 2 failures in the 366/368 baseline. | **resolved** — submodule updated to `9fabbdddf`; the same 2 tests now pass (`2/2`, `True`). Not a repository bug. | T-014, T-020 |

---

## Entries

<!-- Append new entries below, newest last. Keep the template headings so entries stay greppable. -->

### B-001 — Stale compiled `opengate_core` breaks `import opengate` with a misleading `AttributeError`
- **Status**: fixed locally (rebuilt); the detection gap is still open (T-008)
- **Category**: environment issue (stale local build) + repository UX gap (detection)
- **Severity**: high (makes the entire suite unrunnable, with a message that misleads)
- **Area**: `core/opengate_core/*.so` (build artefact) vs. `opengate/actors/digitizers.py`
- **Symptom**:
  ```
  File "opengate/actors/digitizers.py", line 574, in <module>
    class DigitizerDeadTimeActor(DigitizerWithRootOutput, g4.GateDigitizerDeadTimeActor):
  AttributeError: module 'opengate_core' has no attribute 'GateDigitizerDeadTimeActor'.
  Did you mean: 'GateDigitizerReadoutActor'?
  ```
  preceded by `RuntimeWarning: GATE PhysicsListBuilder registry differs from the linked Geant4: * missing C++ bindings: FTFP_BERT, …`.
- **Reproduce**: `"$OPEN_GATE_ENV/bin/python" -c "import opengate"` (or
  `opengate_tests -t actors/test008_dose_actor.py`) on an editable `opengate_core` whose
  compiled extension predates the C++ sources.
- **Environment**: commit `8f049324`, Ubuntu, Python 3.14.7, editable installs of both
  packages, `opengate_core` at one version against a tree at another; the `.so` was dated
  four months **older** than the `.cpp` files it wraps.
- **Suspected cause**: `GateDigitizerDeadTimeActor` exists in `core/opengate_core/opengate_lib/digitizer/` and is registered in `core/opengate_core.cpp` (init + call), so this is **not** a missing binding in the sources — only the compiled `.so` is out of date. Editable installs pick up Python changes immediately but never re-run CMake on their own.
- **Workaround / fix**: `cd core && CMAKE_PREFIX_PATH=<g4>:<itk> … install -v -e .`, then refresh `opengate` too. Rebuild cleared both the `AttributeError` and the physics-list warning (they share the root cause). Verified: `import opengate` clean, `opengate_tests -t actors/test008_dose_actor.py` → `1/1` passed.
- **Why the runner missed it**: `check_environment()` only warns about the Geant4 version and checks the data folder; it never inspects `opengate_core` (T-008).
- **Related**: `skills/environment-setup` §4.6.

### B-002 — Test runner hardcodes `python`, breaking un-activated venvs
- **Status**: confirmed, open (T-007)
- **Category**: repository bug (robustness), surfaced by an environment mistake
- **Severity**: medium (opaque mass failure; trivially avoided once known)
- **Area**: `opengate/bin/opengate_tests_helpers.py:344` (and `:381`)
- **Symptom**: every test fails, including the automatic first-run probe:
  ```
  Running: misc/test001_g4threevector.py    FAILED !   0.0 s
  …
  ModuleNotFoundError: No module named 'opengate'
  Summary pass: 0/1 passed the tests
  ```
  while the runner process itself imported `opengate` successfully.
- **Reproduce**: run the environment's `opengate_tests` **by absolute path without
  activating**, e.g. `"$OPEN_GATE_ENV/bin/opengate_tests" -t actors/test008_dose_actor.py`,
  on a system where `python` resolves to the system interpreter rather than the venv's.
- **Environment**: commit `8f049324`, Ubuntu, a `uv` venv, system `python` at a different
  installation than `$OPEN_GATE_ENV`.
- **Suspected cause**: `cmd = f"python {path_tests_src / f}"` is executed through the shell, so the test subprocess resolves `python` from `PATH` rather than using `sys.executable`. A pre-existing `FIXME` at line 340 documents this as intentional for Windows compatibility.
- **Workaround**: always `source "$OPEN_GATE_ENV/bin/activate"` before running the suite
  (documented in `skills/environment-setup` §3.1).
- **Related**: T-007.

### B-003 — Skill documents disagreed with the code in three places
- **Status**: fixed in this branch
- **Category**: repository bug (our own docs)
- **Severity**: low (they cost real time to debug)
- **Area**: `skills/environment-setup/SKILL.md`, `skills/running-tests/SKILL.md`, `AGENTS.md`
- **Symptoms**: (1) the example `opengate_tests -t source/test008_dose_actor.py` aborts with `Exception: Explicit test paths must point inside the OpenGATE tests/src folder` — the file is `actors/test008_dose_actor.py`; (2) `python -m pip …` fails with `No module named pip` on a `uv`-created venv; (3) the activation requirement was not stated, which is what triggers B-002.
- **Suspected cause**: written from reading the tree, not from running it. `-t` paths are resolved relative to `opengate/tests/src` **including** the subdirectory (`select_tests_by_explicit_paths`).
- **Workaround / fix**: all three corrected this branch, each now citing the observed failure.
- **Related**: T-006.

### B-004 — [ENVIRONMENT, not a repo bug] Geant4 11.4.0 installed where CI pins 11.4.2
- **Status**: open — must be fixed by upgrading the **local Geant4 build** (T-012)
- **Classification**: **environment configuration issue, not a defect in this repository.**
  The Geant4 checkout simply sits on an older release; no source change here is needed.
- **Severity**: high *for the validity of local results* — a full-suite run in this
  environment is not comparable with CI.
- **Area**: the Geant4 source/build referenced by `$OPEN_GATE_DEPS`, linked into
  `opengate_core`.
- **Symptom**: every `opengate_tests` run prints the warning
  `Geant4 version is not ok. This means the environment is not completely up to date`
  (`Detected: geant4-11-04 [MT]`, `Required: v11.4.2`).
- **Cause**: the Geant4 checkout is at tag **`v11.4.0`** (branch `geant4-11.4-release`, commit
  `b4a16de652`, header `#define G4VERSION_NUMBER 1140`). Geant4 spells 11.4.0 as
  `geant4-11-04` and patch 2 as `geant4-11-04-patch-02` (`G4VERSION_NUMBER 1142`), so the
  detected string is correct and the build is genuinely one patch release behind.
- **Fix**: update the Geant4 source to `v11.4.2`, rebuild it, then relink `opengate_core`
  (see the environment guide for the build and relink steps).
- **Note**: this was initially logged as a repository bug; it is not. Only B-005 below is an
  actual code defect.
- **Related**: T-012.

### B-005 — Required Geant4 version is read from a non-existent CI job
- **Status**: confirmed, open (T-013) — **fix verified but not applied** (out of scope this stage)
- **Category**: repository bug (real code defect)
- **Severity**: low (the hard-coded fallback happens to be correct today)
- **Area**: `opengate/bin/opengate_tests_helpers.py`, `get_required_g4_version()` (line 74–81)
- **Symptom**: the function is supposed to read the pinned version from `main.yml`, but:
  ```python
  g4 = githubworfklow["jobs"]["build_wheel"]["env"]["GEANT4_VERSION"]
  ```
  raises `KeyError: 'build_wheel'` — the job names are `build_opengate_wheel`,
  `build_opengate_core_wheel_pr`, … — so the `except`/fallback path returns the hard-coded
  `"v11.4.2"` instead of the real CI pin.
- **Verified**: `GEANT4_VERSION` sits in the **workflow-level** `env:` block of `main.yml`
  (a sibling of `jobs:`), confirmed by reading the file. A further latent defect was found:
  `tests_dir.parents[2]` raises `IndexError` on any path fewer than 3 levels deep, *before*
  the `fpath.exists()` guard runs — so the ``"Safe fallback"`` is unreachable for shallow
  paths.
- **Fix prepared and tested** (reverted, pending scope): read
  `github_workflow["env"]["GEANT4_VERSION"]` with a `(KeyError, TypeError)` guard, and
  length-check `tests_dir.parents` before indexing. Runtime proof on the prepared patch:
  real path → `v11.4.2`; with the pin temporarily edited to `v11.9.9` the call returned
  `v11.9.9`, showing it now tracks the file rather than the literal; shallow path → fallback
  instead of `IndexError`.
- **Reproduce**: parse `.github/workflows/main.yml` and index `jobs.build_wheel.env`.
- **Impact**: if CI's `GEANT4_VERSION` is bumped, the test runner keeps validating against
  the stale literal, so the check can no longer protect the suite.
- **Related**: B-004, T-013.

### B-002 — *(see T-007)* test runner hardcodes `python`, breaking un-activated venvs
- **Status**: confirmed, open (T-007) — **fix verified but not applied** (out of scope this stage)
- **Severity**: medium (opaque mass failure; trivially avoided once known)
- **Verified fix**: after replacing `cmd = f"python {path_tests_src / f}"` with an argument
  list `[sys.executable, str(...)]` run via `subprocess.run(..., shell=False)` (as the two
  in-code `FIXME`s ask, without POSIX quoting), B-002's exact repro passes: with
  `which python` → **`python not found`** on this machine, `"$OPEN_GATE_ENV/bin/opengate_tests"
  -t actors/test008_dose_actor.py` still reported `1/1` and `True`.
- **Note**: this stages' constraint forbids edits outside `skills/`/`AGENTS.md`, so the patch
  was reverted; the two `FIXME` comments in `run_one_test_case` and `run_one_test_case_mp`
  still document the intended change.
- **Related**: T-007, and `skills/environment-setup` §3.1.

### B-006 — Full-suite run leaves an untracked `simulation.json` in the repository root
- **Status**: confirmed, open (T-015)
- **Category**: repository bug (test hygiene / missing ignore rule)
- **Severity**: low (pollutes `git status`; risks being committed by accident)
- **Area**: the test that serialises the simulation dump + `.gitignore`
- **Symptom**: after a full `opengate_tests` run, `git status` reports an untracked
  `simulation.json` at the repository root (a serialised simulation dump beginning
  `{"user_info": {…}}`). `git check-ignore` does **not** match it, and the file is dated
  during the run.
- **Reproduce**: run `opengate_tests` from `$OPEN_GATE_REPO`, then `git status --short`.
- **Impact**: an agent following "never commit generated artifacts" must notice it by hand;
  otherwise it can slip into a commit.
- **Suggested fix**: make the offending test write under `opengate/tests/output*/` (already
  ignored), or add the produced filename to `.gitignore`.
- **Related**: T-015.

### B-008 — Missing reference data looks like a failing test, not a missing dataset
- **Status**: confirmed, open (T-021)
- **Category**: repository bug (error-reporting quality)
- **Severity**: low (misdiagnosis trap; the data itself is fine upstream)
- **Area**: `opengate/tests/utility.py`, `create_output_ref()` (and the tests using it)
- **Symptom**: with the test-data submodule behind, `geometry/test102_gammex467.py` fails
  with a data-comparison error and `geometry/test107_macaco1_mt.py` fails on a missing
  reference, even though nothing is wrong with the code or the Geant4 build. The log shows
  the reference directory existing but empty:
  ```
  Exception: Error while reading the file 'output_ref/test102_gammex467/gammex467.mhd'
  ```
- **Reproduce**: check out `opengate/tests/data` at an older commit
  (`git -C opengate/tests/data checkout 1f89d1f`) and run the two tests above.
- **Root cause of the confusion**: `create_output_ref()` calls
  `mkdir(parents=True, exist_ok=True)`, so a missing dataset yields a **present but empty**
  directory rather than an obvious “reference data missing” state. Note `git` never tracks
  empty directories, so `git status` inside the submodule looks clean too.
- **Confirmed not a repository bug**: after `git submodule update --init opengate/tests/data`
  (now at `9fabbdddf`), both tests pass — `Summary pass: 2/2`, `True`, logs ending with
  “Great, tests are ok.”, including the test107 physics assertion
  (FWHM within tolerance).
- **Suggested improvement**: have the reference-data helper assert that the expected files
  exist and raise a clear “reference data missing — update the submodule” error.
- **Related**: B-009 (the environment cause), T-014, T-021.

### B-007 — `core/setup.py` hardcoded a build parallelism of 4
- **Status**: **fixed in this branch** (uncommitted at time of writing)
- **Category**: repository bug
- **Severity**: medium (build time, not correctness)
- **Area**: `core/setup.py`, `CMakeBuild.build_extension()`
- **Symptom**: `opengate_core` never compiled with more than 4 jobs, so a cold build took
  many minutes even on a 16+ core machine; `make -j $(nproc)` in the build directory was
  visibly faster than the supported `pip install -e .` path.
- **Cause**: `build_args += ["--", "-j4"]` (Unix) and `build_args += ["--parallel", "4"]`
  (Windows, non-Visual-Studio generator).
- **Fix**: default to `os.cpu_count()`, overridable with `OPEN_GATE_BUILD_JOBS`. Both the Unix
  and Windows branches now use the computed value.
- **Verification**: the value is computed at build time; re-running a build should now spawn
  `os.cpu_count()` compile processes. Confirm with `nproc` against the number of `cc1plus`
  processes during a build.
- **Related**: T-018, and `skills/environment-setup` §4.3.

### B-010 — Skills indexes link to `skills/build-and-ci/SKILL.md`, which does not exist
- **Status**: **fixed in this branch** (T-026) — the missing skill was written
- **Category**: repository bug (broken cross-reference in our own docs)
- **Severity**: low (an agent following the index hits a dead end and may conclude the tree is corrupt)
- **Area**: `AGENTS.md:87`, `skills/README.md:18` and `:43`, `skills/status/project-status.md:174`
- **Symptom**: every entry point that maps the skills directory advertised a
  `build-and-ci` skill covering "wheels, CI topology, version bump", but
  `ls skills/` showed only `README.md`, `architecture`, `code-style`, `documentation`,
  `engineering`, `environment-setup`, `running-tests`, `status`.
- **Reproduce**: `ls -d skills/build-and-ci` → `No such file or directory`.
- **Impact**: the three top-level indexes disagreed with the tree; a reader could not tell
  whether the skill was deleted, renamed, or never written.
- **Root cause**: **B-011** — the directory is matched by `.gitignore:40` (`build*/`), so its
  contents can never be committed. The skill was therefore not merely "forgotten"; it was
  structurally impossible to add until the ignore rule was corrected.
- **Resolution**: corrected `.gitignore` (B-011), then wrote the missing skill
  `skills/build-and-ci/SKILL.md`, grounded in the real files: all seven `main.yml` job names
  were grepped and confirmed, and the `opengate-core==<VERSION>` pin (`setup.py:15`), the
  `VERSION` reads (`core/setup.py:30`), the cron trigger (`0 0 * * 0,3`),
  `paths-ignore: docs/**` and the tag-only publish were each verified.
- **Related**: B-011 (the cause), T-024, T-026, and `skills/README.md` §"Adding a new skill"
  (rule 3 requires index updates — this is the reverse case: an index entry requires the skill
  to exist *and* to be committable).

---

## Closed

| id | summary | resolution | commit |
| --- | --- | --- | --- |
| B-010 | Skills indexes linked to a non-existent `skills/build-and-ci/SKILL.md`. | Wrote `skills/build-and-ci/SKILL.md` (grounded in the real `main.yml` job names and pins); all references now resolve. Cause was B-011. | uncommitted on `agentic-skills` (T-026) |
| B-011 | `.gitignore`'s `build*/` silently ignored `skills/build-and-ci/`, making the B-010 fix un-committable. | Added `!skills/build*-*/`; skill now tracked, real build/dist/output paths still ignored. | uncommitted on `agentic-skills` (T-026) |

---

## Common false positives (check before logging)

Distinguish these from real bugs; they waste the most time:

| Symptom | Likely cause | Check |
| --- | --- | --- |
| Import error for `opengate_core` | wrong venv / missing local build | `skills/environment-setup` §7 |
| Many tests failing on missing input files | `opengate/tests/data` submodule not initialized **or behind the recorded pointer** (B-008/B-009) | `ls opengate/tests/data`; then `git submodule update --init --recursive` and compare `git -C opengate/tests/data rev-parse HEAD` with `git ls-tree HEAD opengate/tests/data` |
| Import error for `torch` / `gaga_phsp` / `pytomography` | optional extras not installed | `skills/environment-setup` §5 |
| `cannot allocate memory in static TLS block` | Geant4 TLS model | `skills/environment-setup` §4.5 |
| Test passes alone, fails in the suite | resource contention (`-n all`) or test interdependence | rerun with `-p sp -n 1`, then with `-f` |
| Stochastic assertion failing at low statistics | test design, not code | inspect the tolerance, not the simulation |
| Behaviour differs from the docs | docs may lag the code | hierarchy of truth in `AGENTS.md` §5 |
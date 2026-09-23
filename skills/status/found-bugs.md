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
| U-003 | medium | `opengate/managers.py`, `core/…/GateImageBox.h`, `core/…/GateVoxelSource.cpp` | Three upstream code defects **confirmed in the tree**: #1096 loguru `logger.remove()`, #800 Geant4 private-header include, #1032 latent `VoxelSource` double free. | confirmed, open upstream, not fixed here | T-032 |
| U-006 | medium | `core/…/digitizer/GateDigiCollectionsRootManager.cpp`, `core/…/digitizer/GateDigiCollection.cpp` | Upstream #1143: **confirmed** serial ROOT write-out in MT — unlocked singleton, `SetNtupleMerging(true)` with the default 4000-entry basket, `AddNtupleRow` called per row. Performance-only, no wrong results. | confirmed, open upstream, not fixed here | T-032 |
| U-009 | low | `opengate/tests/src/contrib/test075_siemens_cios_alpha.py`, `source/test044_pbs_rot_transl.py` | Upstream test-quality debt: #844 (test asserts nothing), #933 (failure misread as flakiness; not in the Linux CI set). | open upstream | T-032 |

### Environment issues (not repository bugs)

| id | severity | area | summary | status | related |
| --- | --- | --- | --- | --- | --- |
| B-004 | high (for result validity) | local Geant4 build | The Geant4 checkout was at `v11.4.0` while the project pins `v11.4.2`, so the full-suite baseline was not CI-comparable. | **resolved** — Geant4 rebuilt at v11.4.2, `opengate_core` relinked; runner prints `Geant4 version is OK` | T-012, T-017 |
| B-009 | high (for result validity) | local `opengate/tests/data` submodule | The test-data submodule was checked out four commits behind the pointer recorded in the parent repo, so reference data for several tests was missing — producing the only 2 failures in the 366/368 baseline. | **resolved** — submodule updated to `9fabbdddf`; the same 2 tests now pass (`2/2`, `True`). Not a repository bug. | T-014, T-020 |

### Upstream GitHub issues (triaged — see §"Upstream issue triage" below)

| Upstream | title (short) | triage verdict | category | logged as |
| --- | --- | --- | --- | --- |
| [#1104](https://github.com/OpenGATE/opengate/issues/1104) | `source.start_time=0` silently overridden | **no longer reproduces — already fixed** | repository bug (fixed) | U-001 |
| [#849](https://github.com/OpenGATE/opengate/issues/849) | Wrong interpolation in `GateGenericSource::UpdateActivityWithTAC` | **no longer reproduces — already fixed** | repository bug (fixed) | U-001 |
| [#1059](https://github.com/OpenGATE/opengate/issues/1059) | `> 2^31` primaries crash mid-simulation | **already fixed** — `GetPlatformMaxPrimariesPerRun()` + warning + test098 | repository bug (fixed) | U-010 |
| [#1107](https://github.com/OpenGATE/opengate/issues/1107) | Tubs vs Hexagon transmits ~25 % fewer photons | **NOT REPRODUCED** — ratio `1.0000` over 3 seeds | not a defect (as reported) | U-002 |
| [#857](https://github.com/OpenGATE/opengate/issues/857) | `RepeatParametrisedVolume` deletes ROOT output files | **NOT REPRODUCED** — repeater is innocent | not a defect (as reported) | U-004 |
| [#1035](https://github.com/OpenGATE/opengate/issues/1035) | `DigitizerHitsCollectionActor` ROOT file not finalized | **NOT REPRODUCED** — `End == size`, `uproot` reads `Hits;1` | not a defect (as reported) | U-004 |
| [#1115](https://github.com/OpenGATE/opengate/issues/1115) | `ShieldingLIQMD_HP_EMZ` not working in 10.1.1 | **NOT REPRODUCED** — configures and runs on 10.1.1/Geant4 11.4.2 | not a defect (as reported) | U-006 |
| [#1135](https://github.com/OpenGATE/opengate/issues/1135) | TLEDoseActor score spikes in 8-thread runs | **real race — fixed on master, in NO release tag** | repository bug (fixed on master) | U-006 |
| [#1143](https://github.com/OpenGATE/opengate/issues/1143) | Mutex contention on ROOT write-out | **CONFIRMED present** — cause identified in the code | repository bug | U-006 |
| [#800](https://github.com/OpenGATE/opengate/issues/800) | `GateImageBox.h` includes a Geant4 **private** header | **confirmed present in the tree** | repository bug | U-003 |
| [#1032](https://github.com/OpenGATE/opengate/issues/1032) | `VoxelSource` potential double free in MT | **confirmed present in the tree** | repository bug | U-003 |
| [#616](https://github.com/OpenGATE/opengate/issues/616) | `scale_itk_image` overrides the original ITK image | **confirmed fixed in the tree** (`array_from_image` = a copy) | repository bug (fixed) | U-005 |
| [#1145](https://github.com/OpenGATE/opengate/issues/1145) | PET crosstalk not implemented in Python | **confirmed: not in the tree** (feature gap) | feature request | U-007 |
| [#1096](https://github.com/OpenGATE/opengate/issues/1096) | `logger.remove()` kills the user's loguru handlers | **confirmed present in the tree** | repository bug | U-003 |
| [#942](https://github.com/OpenGATE/opengate/issues/942) | `Cannot import opengate_core` (missing Qt6 .so) | **environment / packaging issue** | environment issue | U-008 |
| [#938](https://github.com/OpenGATE/opengate/issues/938) | same Qt6 `cannot open shared object file`, `[novis]` does not help | **environment / packaging issue** | environment issue | U-008 |
| [#1000](https://github.com/OpenGATE/opengate/issues/1000) | ITK build fails on Linux with GCC 15 | **environment/doc gap** (`geant4-itk.md`) | environment issue | U-008 |
| [#844](https://github.com/OpenGATE/opengate/issues/844) | `test075_siemens_cios_alpha.py` is not a proper test | **confirmed** (test does not assert) | repository bug (tests) | U-009 |
| [#933](https://github.com/OpenGATE/opengate/issues/933) | flakiness on `source/test044_pbs_rot_transl.py` | **open upstream, test design** | repository bug (tests) | U-009 |
| [#1141](https://github.com/OpenGATE/opengate/issues/1141) | “Geant4 version is not ok” on `opengate_tests` | **already known — this is B-004/B-005** | environment + runner bug | B-004, B-005 |

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
- **Verified fix (not yet applied)**: replacing `cmd = f"python {path_tests_src / f}"` with an
  argument list `[sys.executable, str(...)]` run via `subprocess.run(..., shell=False)` (as the
  two in-code `FIXME`s ask, without POSIX quoting) makes B-002's exact repro pass: with
  `which python` → **`python not found`** on this machine,
  `"$OPEN_GATE_ENV/bin/opengate_tests" -t actors/test008_dose_actor.py` still reported `1/1`
  and `True`. The patch was reverted because only `skills/`/`AGENTS.md` were in scope; the two
  `FIXME` comments in `run_one_test_case` and `run_one_test_case_mp` still document it (T-029).
- **Related**: T-007, T-029, and `skills/environment-setup` §3.1.

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

### B-009 — [ENVIRONMENT, not a repo bug] test-data submodule behind the recorded pointer
- **Status**: **resolved** — `git submodule update --init opengate/tests/data` (now at `9fabbdddf`)
- **Category**: environment issue (submodule checkout state), **not** a repository bug
- **Severity**: high *for result validity* — it produced the only 2 failures in the 366/368 baseline
- **Area**: `opengate/tests/data` (binary submodule) vs. the pointer recorded in the parent repo
- **Symptom**: `geometry/test102_gammex467.py` fails with a data-comparison error and
  `geometry/test107_macaco1_mt.py` fails on missing reference data, while the code and the Geant4
  build are both correct.
- **Cause**: the submodule was checked out four commits behind the pointer recorded in the parent
  repo, so `output_ref/` directories were absent (see B-008 for why that misleads).
- **Fix**: `git submodule update --init opengate/tests/data`; the two tests then pass
  (`Summary pass: 2/2`, `True`, logs ending with “Great, tests are ok.”).
- **Related**: B-008 (the misleading reporting), T-014, T-020.

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

### U-001 — Upstream start-time / TAC-interpolation bugs are already fixed in this tree
- **Status**: verified fixed — nothing to do, **do not re-log as open**
- **Category**: repository bug (already resolved upstream in this tree)
- **Upstream**: [#1104](https://github.com/OpenGATE/opengate/issues/1104) and
  [#849](https://github.com/OpenGATE/opengate/issues/849) — both still shown **open** on GitHub,
  so they look like live defects; they are not.
- **Area**: `opengate/sources/base.py` `SourceBase.initialize_start_end_time` (line 117), and
  `core/opengate_core/opengate_lib/GateGenericSource.cpp` `UpdateActivityWithTAC` (line 108).
- **What the report says**: (a) #1104 — `if not self.start_time:` treats `start_time = 0.0` as
  unset, so every job of a split simulation resets the decay clock to its own run start.
  (b) #849 — the TAC bin index is one too high and the two interpolation weights are swapped.
- **Checked in the current tree** (`996572b64`): `base.py:117` reads `if self.start_time is None:`
  — exactly the fix #1104 asks for (`git log -L 112,121:opengate/sources/base.py` → commit
  `100401286` “Fix start_time/stop_time default handling in SourceBase”). `GateGenericSource.cpp`
  now clamps with `if (i == 0) { fActivity = fTAC_Activities[0]; return; }`, then `i -= 1`
  (the “move to the lower bin edge” correction) and weights
  `fTAC_Activities[i] * (t[i+1]-time)/dt + fTAC_Activities[i+1] * (time-t[i])/dt` — the same
  algebra as the “GOOD INTERPOLATION” in the report.
- **Action**: nothing in the repo. The upstream issues can be closed; the *only* reason to touch
  them here is the `end_time` sibling, which was fixed in the same commit.
- **Related**: —

### U-002 — `Tubs` vs area-matched `Hexagon` transmission gap: **NOT REPRODUCED**
- **Status**: **dismissed as reported** — my controlled reproduction gives ratio **1.0000**
- **Category**: not a defect (on the evidence available here)
- **Severity**: n/a (was logged as high if real; the measurement below says it is not real)
- **Upstream**: [#1107](https://github.com/OpenGATE/opengate/issues/1107) (opened 2026-07-28,
  OpenGATE 10.1.0, Python 3.10, Ubuntu 22.04)
- **What the report claims**: two holes of *exactly* matched open cross-sectional area
  (0.5261 mm²), one `Tubs` one `Hexagon`, in tungsten; a parallel 140 keV beam gives 10.69 % vs
  8.02 % transmission under normal incidence (ratio 0.750, expected ≈ 1.0), stable at ~0.73–0.75
  across 9 isolation variants.
- **What I ran** (commit `996572b64`, Geant4 11.4.2, Python 3.12, macOS x86_64, 1 thread):
  a boolean `Box(G4_W) − hole` for each shape, each hole sized **from the same target area**
  (`Tubs` `rmax = sqrt(A/pi) = 0.40922 mm`; `Hexagon` circumradius `0.45 mm`, i.e. across-flats
  `0.77942 mm`), a **true parallel beam** along +Z (`direction.type = "momentum"`,
  `momentum = [0,0,1]`), and a `PhaseSpaceActor` on a 10×10 mm plane immediately behind the block.
- **Result**: `tubs = 500032`, `hex = 500026` out of 500 000 primaries each → **ratio 1.0000**.
  Re-run with seeds 1, 2 and 3: **ratio 1.0000 each time**. No gap of any size, let alone 25 %.
- **Harness validation** (mandatory — see U-004's note): the same beam through an *empty* air
  world transmits ~100 % (50 003/50 000), so the 0.0 % failures I first saw were my own bug, not
  the code's. The final numbers come from a harness that passes that check.
- **Likely explanation of the original report**: the reporter's `Hexagon` radius convention.
  GATE's `Hexagon.radius` is the **circumradius**; using it as the across-flats changes the open
  area by a factor of **3**. Alternatively their beam was not truly parallel (see
  [`engineering/gate-physics-expert.md`](../engineering/gate-physics-expert.md) §4.1 — `beam2d`
  with `sigma=0` is *not* a parallel beam). Either way the effect is in the *setup*, not in
  `G4Tubs`/`G4Polyhedra` construction.
- **Caveat**: I did not run the reporter's attached script and did not reproduce their exact
  9-variant lattice. My conclusion covers the *geometric* claim (equal-area holes transmit
  equally), which is what the issue is about.
- **Related**: [`engineering/gate-geometry-expert.md`](../engineering/gate-geometry-expert.md) §4.2
  (the area formulas and the circumradius trap).

### U-003 — Three upstream code defects confirmed in the tree (not fixed here)
- **Status**: confirmed present at commit `996572b64`; **not fixed in this change** (out of scope)
- **Category**: repository bug
- **Severity**: [#1096](https://github.com/OpenGATE/opengate/issues/1096) medium (silently
  discards the *user's* logging), [#800](https://github.com/OpenGATE/opengate/issues/800) medium
  (blocks source builds without Geant4 private headers), [#1032](https://github.com/OpenGATE/opengate/issues/1032)
  medium (latent double free, MT-only)
- **Confirmed here**:
  - [#1096](https://github.com/OpenGATE/opengate/issues/1096) — `_setter_hook_verbose_level` calls
    a bare `logger.remove()` (`opengate/managers.py:1772`) when `log_handler_id == -1`. Loguru's
    `remove()` with no argument removes **every** handler, including handlers the user added
    themselves, so `logger.add('run.log')` is silently dropped on the first simulation. The fix is
    to remove only the id GATE itself added (it already does this in the `else` branch, line 1776).
  - [#800](https://github.com/OpenGATE/opengate/issues/800) — `core/opengate_core/opengate_lib/GateImageBox.h:35`
    has `#include <private/G4OpenGLSceneHandler.hh>`, a Geant4 **internal** header that is not
    installed by a normal Geant4 installation. It is guarded by `USE_VISU`/`G4VERSION_NUMBER`,
    so a no-visu build is unaffected, but any build enabling Qt/OpenGL against a stripped Geant4
    fails. Reported as breaking builds; no in-tree workaround.
  - [#1032](https://github.com/OpenGATE/opengate/issues/1032) — `GateSingleParticleSource`'s
    destructor `delete`s `fPositionGenerator`, and `GateVoxelSource.cpp` hands it a
    `fVoxelPositionGenerator` via `SetPosGenerator`, which the caller still owns. Benign only
    while that destructor never runs on a worker thread — i.e. a latent double free, not yet a
    crash. Upstream labels it `bug`.
- **Action**: not fixed here. Each needs its own branch, a test that fails first, and (for #800)
  a confirmed skip-if-no-private-headers path.
- **Related**: this is the same *class* as the local-logging work in
  [`engineering/simulation-debugger.md`](../engineering/simulation-debugger.md).
  ([#1059](https://github.com/OpenGATE/opengate/issues/1059) was in this group and is now
  **fixed** — see U-010.)

### U-004 — Two upstream actor-output claims: **NOT REPRODUCED**
- **Status**: **both dismissed as reported** at commit `996572b64`
- **Category**: not a defect (on the evidence available here)
- **Severity**: n/a (were logged as high if real)
- **Upstream**: [#857](https://github.com/OpenGATE/opengate/issues/857) (opened 2025-12-04) and
  [#1035](https://github.com/OpenGATE/opengate/issues/1035) (opened 2026-05-23).
- **What they claim**:
  - #857 — merely *constructing* a `RepeatParametrisedVolume` (never added to the volume manager)
    causes every digitizer `.root` file to be deleted at the end of the run, while `stat.txt`
    survives.
  - #1035 — a `DigitizerHitsCollectionActor` `.root` file is left **unfinalized** (ROOT header
    `End == 252`, `uproot.open(f).keys() == []`) with a complex phantom and/or several modules.
- **#857 — what I ran**: the reporter's own two-case script (with and without the
  `RepeatParametrisedVolume(...)` construction line), each writing to its own temp dir.
  **Result: the ROOT file was absent in BOTH cases** — so the repeater is *not* the cause.
  The real reason was that the source (a 100 kBq point source in a 1 m air world) produced **zero
  hits** in the 10 cm detector, and GATE then reports
  `⚠️ Empty output, no particles stored in …root` and correctly writes no file. Once the source
  actually irradiates the detector, the `.root` file is produced and readable
  (`uproot keys: ['Hits;1']`). **The repeater does not delete anything.**
- **#1035 — what I ran**: a NEMA-like phantom (water cylinder + 22 mm sphere) plus a 35×5×315 mm
  CZT module, a 140.5 keV source inside the phantom, **2 threads** and 20 000 primaries, exactly
  the trigger conditions reported. **Result: the file is correctly finalized** — ROOT header
  `End` equals the file size (not 252) and `uproot.open(...).keys()` returns `['Hits;1']`.
  **Not reproduced.**
- **Honest caveat**: #1035's reporter sees the failure only in *their* larger geometry (more
  modules / more primaries). My reduced case is a faithful trigger but not a bit-for-bit copy of
  theirs, so I can say "not reproduced here" — not "impossible".
- **Harness note (this is why the section exists)**: my first #857 attempt produced exactly the
  symptom the issue describes — *no ROOT file* — and it was **my own harness**, not the code. Only
  after validating the harness (does the same beam deposit energy in the detector at all?) did the
  real picture appear. The traps I hit are now catalogued in
  [`engineering/simulation-debugger.md`](../engineering/simulation-debugger.md) §5.1.
- **Note on the related closed issues**: `#1034`/`#1033` (same title as #1035) and `#1109` (“Actor
  on Repeated Volume…”) were all closed as completed, so this area has changed since the reports.
- **Related**: B-006 (another “test leaves/takes files” hygiene bug), T-015.

### U-005 — `scale_itk_image()` aliasing: **already fixed in the tree**
- **Status**: **fixed** — the code now takes a copy, which is what the issue asked for
- **Category**: repository bug (already resolved)
- **Severity**: n/a
- **Upstream**: [#616](https://github.com/OpenGATE/opengate/issues/616)
- **Checked in the tree**: `opengate/image.py:361` — `scale_itk_image` now starts with
  `imgarr = itk.array_from_image(img)`, i.e. a **copy**; the report's premise
  (`array_view_from_image`, which aliases) no longer holds. The neighbouring functions remain
  inconsistent — `add_constant_to_itk_image` (line 408) explicitly `.copy()`s a view, while
  `divide_itk_images` (line 377) uses two views without copying — but a divide writes to a *new*
  output image, so it is not an aliasing bug.
- **Action**: nothing here. The reporters said they would open the PR; upstream can close it.
- **Related**: —

### U-006 — Physics/performance claims: one dismissed, two resolved via upstream analysis
- **Status**: #1115 **NOT REPRODUCED**; #1135 **explained & fixed on master**; #1143 **confirmed present, cause identified**
- **Category**: #1115 not a defect; #1135 a real race, **already fixed in this tree**; #1143 a real
  design issue, **still present**
- **Upstream**: [#1115](https://github.com/OpenGATE/opengate/issues/1115),
  [#1135](https://github.com/OpenGATE/opengate/issues/1135),
  [#1143](https://github.com/OpenGATE/opengate/issues/1143)
- **#1115 — what I ran**: `ShieldingLIQMD_HP_EMZ` (and `ShieldingLIQMD_HP`, `Shielding_HP_EMZ`,
  `Shielding_EMZ`) as `sim.physics_manager.physics_list_name`, then a full 1-thread run
  (20 mm air world, 1 MeV gammas, 1000 primaries) on **GATE 10.1.1 + Geant4 11.4.2**. All four
  configured, initialized and ran to completion; the baseline `G4EmStandardPhysics_option4` behaved
  identically. **Not reproduced** on the pinned Geant4.
- **#1135 — resolved by reading the issue thread, not by re-running it**: the maintainers' comments
  identify the cause as **thread races in the TLE bookkeeping** (`GateTLEDoseActor` accumulating
  per-thread partial sums), producing rare *upward* spikes in individual voxels while the co-scored
  `DoseActor` (a different accumulation path) stays clean. It was **fixed on `master`** by commit
  `a92a62bf1` (“fix thread race issue”).
- **#1135 — verified in this tree**: `git cat-file -t a92a62bf1` → commit, and
  `git merge-base --is-ancestor a92a62bf1 HEAD` → **true**, so the fix **is present here**
  (64 commits after it). The fix is real and inspectable: the racy shared
  `fLastEnergy`/`fLastMu` members were replaced by **`thread_local` caches** — see
  `core/opengate_core/opengate_lib/GateMaterialMuHandler.cpp:69-71`
  (`thread_local … lastHandler / lastCouple / lastTable`).
- **#1135 — the caveat that matters most**: `git tag --contains a92a62bf1` returns **nothing**;
  the newest release tag is `10.1.1` and it does **not** contain the fix. So “I am on 10.1.1 and
  still see the spikes” is expected, and the issue must **not** be closed as “fixed in the latest
  release” — it is fixed **on master only**. This also means re-running it *here* would have been
  misleading: this tree is `master`+64, so it would have looked clean and I would have wrongly
dismissed a real bug. **The lesson: a claim about a released version cannot be tested on a tree
  that is ahead of that release** (see
  [`engineering/simulation-debugger.md`](../engineering/simulation-debugger.md) §5.1).
- **#1143 — confirmed present, mechanism read in the code**: the comments describe serial ROOT
  write-out in MT. Verified in the tree:
  - `GateDigiCollectionsRootManager.cpp:41-43` calls `ram->SetNtupleMerging(true)` in MT mode,
    with the adjacent comment (lines 30-32) that `SetBasketEntries`/`SetBasketSize`
    “does not seem to work (default is 4000)” — the small basket size is what makes the mutex
    contention hot;
  - the singleton is created **without a lock** (`if (fInstance == nullptr) fInstance = new …`,
    line 18) — a genuine lazy-init race;
  - `GateDigiCollection.cpp:125` calls `am->AddNtupleRow(fTupleId)` **per row**, so every hit
    crosses the shared analysis-manager lock;
  - `opengate/coordinators.py:121` (`RootMergeCoordinator`) merges split-job outputs and is **not**
    a solution for the per-thread `_nt_` files.
  `git log -L` shows the `SetNtupleMerging` call dates from **2023** (`d19e408f2`), i.e. this is a
  long-standing design choice, not a regression.
- **Action**: #1135 needs no code work here — it is fixed on master; the useful action is to
  **say so upstream and note that no release contains it** (a backport/release decision for the
  maintainers). #1143 is a genuine open defect: it needs its own branch, a benchmark measuring
  write-out scaling against thread count, and a fix (raise the basket size / batch rows per event
  instead of per row / guard the singleton). Neither is fixed in this change.
- **Related**: B-001 (the `PhysicsListBuilder registry differs from the linked Geant4` warning),
  [`engineering/geant4-physics-expert.md`](../engineering/geant4-physics-expert.md).

### U-010 — `> 2^31` primaries: **already fixed in the tree**
- **Status**: **fixed** — the crash was replaced by an explicit limit, a warning and a test
- **Category**: repository bug (already resolved)
- **Upstream**: [#1059](https://github.com/OpenGATE/opengate/issues/1059)
- **What the report said**: `GateSourceManager.cpp` emitted `/run/beamOn INT32_MAX` with
  `fMaxPrimariesPerRun = INT32_MAX`, so more than `2^31` primaries in one run overflow the `G4int`
  taken by `G4RunManager::BeamOn` and the process dies *mid-simulation*.
- **Checked in the tree**: the limit is now **platform-aware** —
  `g4.GateSourceManager.GetPlatformMaxPrimariesPerRun()` (`opengate/engines.py:71`) — and reaching
  it triggers `GateSourceManager::WarnPrimaryLimitReached()`
  (`core/opengate_core/opengate_lib/GateSourceManager.cpp:105`), which emits a `JustWarning`
  G4Exception explaining that the run is being stopped **before** generating more primaries instead
  of aborting. There is a `max_primaries_per_run` user option, documentation in
  `user_guide_sources.rst`, and a regression test.
- **Verified**: `opengate_tests -t source/test098_stop_simulation_at_max_primaries.py` →
  `Summary pass: 1/1`, `True` (run on this machine, commit `996572b64`).
- **Action**: none. Upstream can close #1059.
- **Related**: U-003 (the other C++ defects, still open).

### U-007 — PET crosstalk: feature gap, not a bug
- **Status**: open upstream, **confirmed absent from the Python API**
- **Category**: feature request (explicitly *not* a bug — do not log it as one)
- **Upstream**: [#1145](https://github.com/OpenGATE/opengate/issues/1145) (opened 2026-09-23)
- **Content**: GATE 9's C++ digitizer has a PET optical-crosstalk model; the reporter asks whether
  the Python API exposes it, or whether `DigitizerSpatialBlurringActor` can substitute (they
  suspect not, for discrete crystals).
- **Verdict**: this is a *missing capability*, and the honest answer is “not implemented in the
  Python layer”. Nothing to fix in this triage; if the user wants it, it is a new actor/feature
  piece, not a defect. Related open upstream items: `#885` (ComptonCameraActor request), `#877`.
- **Related**: [`engineering/gate-physics-expert.md`](../engineering/gate-physics-expert.md)

### U-008 — Upstream issues that are environment problems, not code defects
- **Status**: open upstream — **do not “fix” the repo for these**
- **Category**: environment issue / documentation gap
- **Upstream**: [#942](https://github.com/OpenGATE/opengate/issues/942) and
  [#938](https://github.com/OpenGATE/opengate/issues/938) (both: `Cannot import opengate_core`,
  `libQt6Core-*.so.6.6.2: cannot open shared object file`, and reinstalling with `[novis]` does not
  help), [#1000](https://github.com/OpenGATE/opengate/issues/1000) (building ITK 5.2.1 fails on
  GCC 15 — `-include cstdint` / `-std=gnu11` needed), [#1141](https://github.com/OpenGATE/opengate/issues/1141)
  (“Geant4 version is not ok”).
- **Why they are not repository bugs**: #942/#938 are a *wheel/install* problem — a Qt6 runtime
  dependency of the installed wheel is missing on the user's machine, so the C++ module cannot be
  dlopen'd; the correct response is to install the Qt6 runtime (or use the `novis` extra
  *correctly*), not to change the sources. #1000 is a toolchain-too-new problem with a proven
  workaround. #1141 is **exactly this log's B-004/B-005**: the reporter's Geant4 is
  `geant4-11-04-patch-02` while the runner prints `Required: v11.4.0` and then `11 4 2` on the next
  line — a self-contradicting message produced by B-005's broken `get_required_g4_version()`.
- **Action**: keep the environment guidance in
  [`environment-setup/geant4-itk.md`](../environment-setup/geant4-itk.md) correct; nothing here
  needs a code change except B-005 (already logged, fix prepared). The ITK/GCC-15 flags are worth
  a one-line note in that same skill if the user builds ITK from source.
- **Related**: B-004, B-005, [`environment-setup/geant4-itk.md`](../environment-setup/geant4-itk.md)

### U-009 — Upstream test-quality issues worth remembering when writing tests
- **Status**: open upstream — neither fixed here
- **Category**: repository bug (tests)
- **Upstream**: [#844](https://github.com/OpenGATE/opengate/issues/844)
  (`test075_siemens_cios_alpha.py` “does not test anything”, plus companion
  [#885](https://github.com/OpenGATE/opengate/issues/885) “test075… and spekpy issue”) and
  [#933](https://github.com/OpenGATE/opengate/issues/933) (reported as flaky; the reporter's own
  edit concludes it is *not* flakiness but a plain failure, and that the test is **not in the Linux
  CI set**).
- **Why it matters**: both are exactly the failure modes
  [`engineering/test-writer.md`](../engineering/test-writer.md) exists to prevent — a test that
  asserts nothing, and a test that passes only because CI never runs it. If you touch the SPECT
  contrib models or the PBS source, check whether these two files are in the run set.
- **Related**: [`engineering/test-writer.md`](../engineering/test-writer.md), [#993](https://github.com/OpenGATE/opengate/issues/993)
  (“Check if actor output is correctly handled in all voxel deposit actors”).

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

---

## Closed

| id | summary | resolution | commit |
| --- | --- | --- | --- |
| B-010 | Skills indexes linked to a non-existent `skills/build-and-ci/SKILL.md`. | Wrote `skills/build-and-ci/SKILL.md` (grounded in the real `main.yml` job names and pins); all references now resolve. Cause was B-011. Supervisor note: T-028 subsequently merged that skill into `environment-setup` §6 and removed the directory, so B-010's fix was itself superseded — no dangling reference remains. | uncommitted on `agentic-skills` (T-026, superseded by T-028) |
| B-011 | `.gitignore`'s `build*/` silently ignored `skills/build-and-ci/`, making the B-010 fix un-committable. | Added `!skills/build*-*/`; skill now tracked, real build/dist/output paths still ignored. The rule is kept even though the directory is gone — it prevents the trap recurring for any future `build*`-named skill. | uncommitted on `agentic-skills` (T-026) |

---

## Upstream issue triage (how this file relates to GitHub)

The rule in the header stands: **things already tracked upstream belong in GitHub issues — link
them, do not duplicate their content.** This section records only *triage*, i.e. what an agent
verified against the local tree, so the next agent does not re-open the same investigation.

- Source of truth: <https://github.com/OpenGATE/opengate/issues> (112 open at the time of this
  triage, 2026).
- Every entry below names the upstream number, the **verdict**, and *what was actually checked*.
- **A verdict is one of three, and they are not interchangeable:**
  - **NOT REPRODUCED** — a controlled reproduction was run here and did *not* show the reported
    behaviour. This is a real, if negative, result.
  - **NOT VERIFIED** — nobody reproduced it in this environment; it is a lead, not a finding.
    Never quote it as confirmed.
  - **CONFIRMED** — read in the code and/or reproduced; a defect.
- **Two rules that decide whether a claim can be tested here at all:**
  1. **Read the issue's comments before re-running anything.** Maintainers often post the root
     cause and the fixing commit; re-deriving it wastes a session (#1135 and #1143 were both
     fully diagnosed in their threads).
  2. **A claim about a *released* version cannot be tested on a tree ahead of that release.**
     #1135 is fixed on `master` but in no tag, so a run in this tree looks clean and would wrongly
     dismiss a real bug. Check `git tag --contains <fix>` before concluding anything.
- **Every reproduction must be validated against a known answer first** — see
  [`engineering/simulation-debugger.md`](../engineering/simulation-debugger.md) §5.1. A harness that
  gives 0 % transmission through air cannot measure a 25 % difference, and reporting its output as
  a confirmed bug is the most expensive mistake in this file.
- When an upstream issue is fixed in a release, move its row out of this section rather than
  silently deleting it (the “already fixed” rows below are the reason a triage section exists at
  all: **five** of the newest-looking issues were already dead).

### The short version
| Bucket | Upstream | What to do |
| --- | --- | --- |
| **NOT REPRODUCED** — controlled run says no | #1107, #857, #1035, #1115 | report back upstream; do not fix |
| Already fixed in the tree, still open upstream | #1104, #849, #1059, #616 | nothing here; upstream can close them |
| **Fixed on `master` but in NO release tag** | #1135 | tell upstream; backport is a release decision (U-006) |
| Confirmed present in the tree, not fixed here | #1096, #800, #1032, #1143 | one branch each, test first (U-003, U-006) |
| Confirmed **absent** (missing feature, not a bug) | #1145 | not a defect (U-007) |
| Environment / toolchain, not the repo | #942, #938, #1000, #1141 | fix the machine or the docs (U-008) |
| Test-quality debt | #844, #933 | relevant when you write tests (U-009) |

---

## Common false positives (check before logging)

Distinguish these from real bugs; they waste the most time:

| Symptom | Likely cause | Check |
| --- | --- | --- |
| Import error for `opengate_core` | wrong venv / missing local build | `skills/environment-setup` §7 |
| Import error for `opengate_core` mentioning `libQt6Core-*.so` | Qt6 runtime missing for the installed wheel (upstream #938/#942) | U-008 — install Qt6 or use the correct no-visu install; do **not** patch the sources |
| `Geant4 version is not ok` printed by `opengate_tests` | local Geant4 is behind the pin (**or** the B-005 mis-parse) | B-004, B-005 |
| A bug report you cannot find in the code any more | it may already be fixed though the issue is still open upstream | U-001 |
| Many tests failing on missing input files | `opengate/tests/data` submodule not initialized **or behind the recorded pointer** (B-008/B-009) | `ls opengate/tests/data`; then `git submodule update --init --recursive` and compare `git -C opengate/tests/data rev-parse HEAD` with `git ls-tree HEAD opengate/tests/data` |
| Import error for `torch` / `gaga_phsp` / `pytomography` | optional extras not installed | `skills/environment-setup` §5 |
| `cannot allocate memory in static TLS block` | Geant4 TLS model | `skills/environment-setup` §4.5 |
| Test passes alone, fails in the suite | resource contention (`-n all`) or test interdependence | rerun with `-p sp -n 1`, then with `-f` |
| Stochastic assertion failing at low statistics | test design, not code | inspect the tolerance, not the simulation |
| Behaviour differs from the docs | docs may lag the code | hierarchy of truth in `AGENTS.md` §5 |

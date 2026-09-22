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
| B-001 | high | `core/` build / `skills/environment-setup` | Stale compiled `opengate_core` made `import opengate` fail with a misleading `AttributeError`; the test runner did not detect it. | fixed locally (rebuilt) — underlying UX gap still open | T-005, T-008 |
| B-002 | medium | `opengate/bin/opengate_tests_helpers.py` | The runner hardcodes `python <test>` instead of `sys.executable`, so an un-activated venv fails all tests with `ModuleNotFoundError: opengate`. | confirmed, open | T-007 |
| B-003 | low | `skills/` (our own docs) | The skills shipped a wrong `-t` example path (`source/test008_dose_actor.py`), a `pip`-only install recipe for a `uv` venv, and omitted the activation requirement. | fixed in this branch | T-006 |

---

## Entries

<!-- Append new entries below, newest last. Keep the template headings so entries stay greppable. -->

### B-001 — Stale compiled `opengate_core` breaks `import opengate` with a misleading `AttributeError`
- **Status**: fixed locally (rebuilt); the detection gap is still open (T-008)
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
- **Severity**: low (our own docs, but they cost real time to debug)
- **Area**: `skills/environment-setup/SKILL.md`, `skills/running-tests/SKILL.md`, `AGENTS.md`
- **Symptoms**: (1) the example `opengate_tests -t source/test008_dose_actor.py` aborts with `Exception: Explicit test paths must point inside the OpenGATE tests/src folder` — the file is `actors/test008_dose_actor.py`; (2) `python -m pip …` fails with `No module named pip` on a `uv`-created venv; (3) the activation requirement was not stated, which is what triggers B-002.
- **Suspected cause**: written from reading the tree, not from running it. `-t` paths are resolved relative to `opengate/tests/src` **including** the subdirectory (`select_tests_by_explicit_paths`).
- **Workaround / fix**: all three corrected this branch, each now citing the observed failure.
- **Related**: T-006.

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
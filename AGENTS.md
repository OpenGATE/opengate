# AGENTS.md — working on the OpenGATE/opengate repository

This file is the **entry point for any AI agent** (or human in a hurry) that has to
modify, test, debug or document this repository. Read it fully before doing anything.
Then open the specific skill you need from [`skills/`](skills/).

> Project: **GATE 10** — Monte Carlo simulation platform for medical physics
> (PET, SPECT, CT, external/internal radiotherapy, dosimetry), built on Geant4.
> Version: see [`VERSION`](VERSION) (currently `10.1.1`).
> Requires Python >= 3.10 (CI tests 3.10 → 3.14). Geant4 `v11.4.2`, ITK `v5.4.4`.

---

## 1. Repository layout (what lives where)

| Path | Content |
| --- | --- |
| `opengate/` | Pure-Python package: user API, managers, engines, actors, sources, geometry, physics, image handling. This is `import opengate`. |
| `opengate/tests/` | Test suite. `src/` contains `testXXX_*.py` scripts, `utility.py` helpers, `data/` (git submodule with binary test data), `log/`, `output/` (generated). |
| `opengate/bin/` | Console entry points (`opengate_tests`, `opengate_info`, `opengate_jobs_*`, `opengate_visu`, …). Declared in `pyproject.toml`. |
| `core/` | C++ subpackage `opengate_core` — pybind11 bindings + Gate C++ library binding Geant4 and ITK. Compiled with CMake. |
| `core/external/` | Vendored submodules: `pybind11`, `fmt`. |
| `docs/` | Sphinx sources (`docs/source/user_guide`, `docs/source/developer_guide`). Published on Read the Docs. |
| `.github/workflows/` | CI: `main.yml` (orchestrator), `actions_build/` (wheel builds), `actions_tests/` (test run + dashboard upload). |
| `pyproject.toml` | Metadata of the Python package `opengate`. |
| `core/setup.py`, `core/pyproject.toml` | Metadata + CMake build of `opengate_core`. |
| `VERSION` | Single source of truth of the version; `opengate` requires `opengate-core==<same version>`. |
| `AGENTS.md`, `skills/` | Agent instructions and skills (this directory). |

Two-package design: `opengate` (Python, fast to install) depends on `opengate_core`
(C++, ships Geant4 + ITK binaries in the published wheels). A **developer install must
compile `opengate_core` locally** — the pip-distributed `opengate_core` wheel does not
match local C++ changes.

## 2. Golden rules

1. **Never run tests against a half-installed tree.** Use a dedicated virtual
   environment and *always* run the suite via the `opengate_tests` entry point
   (never bare `python testXXX.py` loops, never `pytest` — this repo uses its own runner).
   See [`skills/environment-setup/SKILL.md`](skills/environment-setup/SKILL.md).
2. **Submodules first.** `git submodule update --init --recursive` before building or
   running tests. Missing `opengate/tests/data` = most tests fail for the wrong reason.
3. **`--recurse-submodules` on clone**, `git lfs` must be installed (test data is large binary).
4. **Formatting is enforced** by `pre-commit` (black for Python, clang-format for C++,
   trailing whitespace). Run it before committing — see [`skills/code-style/SKILL.md`](skills/code-style/SKILL.md).
5. **Version bump = 3 places**: `VERSION` at root, and the release must republish both
   `opengate` and `opengate_core` (`opengate-core==10.1.1` is a hard pin in `setup.py`).
6. **Never commit generated artifacts**: `opengate/tests/output*/`, `opengate/tests/log/`,
   `dist/`, `build/`, `*.egg-info`, images/root files (see `.gitignore`).
7. **Keep `skills/status/found-bugs.md` up to date** whenever you discover a bug you do
   not immediately fix, and `skills/status/task-list.md` when you plan/close work.
8. **Do not run the whole suite casually**: it takes tens of minutes, downloads Geant4
   data on first run, and needs ~all cores. Use `--start_id/--end_id`/`-t` filters.
9. **Cite real evidence.** Do not claim a test passed unless you ran it (or read the CI
   result). Do not invent Geant4/actor parameter names — grep the code and docs first.

## 3. Skills index

| Skill | Use it when |
| --- | --- |
| [`skills/environment-setup/`](skills/environment-setup/SKILL.md) | You need a working virtual dev environment where **all tests** run (venv, Geant4/ITK, `pip install -e .`, optional extras). |
| [`skills/running-tests/`](skills/running-tests/SKILL.md) | You must run, filter, debug or interpret the test suite and its dashboard output. |
| [`skills/build-and-ci/`](skills/build-and-ci/SKILL.md) | You touch `core/`, wheels, `pyproject.toml`, or the GitHub Actions workflows. |
| [`skills/code-style/`](skills/code-style/SKILL.md) | Before every commit: formatting, naming, imports, docstrings. |
| [`skills/architecture/`](skills/architecture/SKILL.md) | You add/modify engines, managers, actors, sources, physics — the object lifecycle in GATE 10. |
| [`skills/documentation/`](skills/documentation/SKILL.md) | You add a user/developer guide page or build the Sphinx docs. |
| [`skills/status/`](skills/status/task-list.md) | You need the shared task list, the bug log, or the project status snapshot. |

## 4. Quick start (30-second version)

```bash
# 1. clone with submodules (git-lfs required)
git clone --recurse-submodules https://github.com/OpenGATE/opengate
cd opengate

# 2. dedicated env (see skills/environment-setup for the full, reliable path)
python3 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip

# 3. Python package, editable (uses the pip-provided opengate_core wheel)
python -m pip install -e .

# 4. smoke test (first run downloads Geant4 + test data — can take a while)
opengate_tests -t source/test008_dose_actor.py
```

For anything involving `core/` (C++), Qt visualization, or a *reproducible* full-suite
run, follow [`skills/environment-setup/SKILL.md`](skills/environment-setup/SKILL.md)
which builds Geant4/ITK and `opengate_core` from source.

## 5. Hierarchy of truth

When sources disagree, trust them in this order:

1. the code in `opengate/` and `core/` (runtime behaviour);
2. the test suite `opengate/tests/src/` (executable specification);
3. `.github/workflows/` (how the maintainers actually build & test);
4. `docs/source/` (may lag behind, especially `DesignGuidelines.md` which is marked **OBSOLETE**);
5. this file and `skills/` (may lag behind the code — fix them if you spot drift).
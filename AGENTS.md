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
| `user_secrets.json` | **Git-ignored, per-machine** absolute paths (`OPEN_GATE_REPO`, `OPEN_GATE_ENV`, `OPEN_GATE_DEPS`). Read by agents before building/running. Create it and ask the user for the values — see `skills/environment-setup` §0.1. |

Two-package design: `opengate` (Python, fast to install) depends on `opengate_core`
(C++, ships Geant4 + ITK binaries in the published wheels). A **developer install must
compile `opengate_core` locally** — the pip-distributed `opengate_core` wheel does not
match local C++ changes.

## 2. Golden rules

1. **Never commit on `master`.** Do all work on a dedicated branch, and make sure it is
   **based on the up-to-date local `master`** before you start (see §6). `master` must stay
   byte-identical to upstream; if you find yourself on `master` with changes, move them to a
   branch (`git switch -c <name>`) before doing anything else.
2. **Never commit without explicit user approval.** Stage and show what would be committed,
   then ask. Do not `git commit`, `git rebase`, `git push`, `git reset --hard` or otherwise
   rewrite/advance history on your own initiative — the user validates the changes first.
3. **Never run tests against a half-installed tree.** Use the user-designated virtual
   environment on **non-volatile** storage (`$OPEN_GATE_ENV`) and *always* run the suite
   via the `opengate_tests` entry point (never bare `python testXXX.py` loops, never
   `pytest` — this repo uses its own runner). Paths come from `user_secrets.json` (see
   below); never invent them. See [`skills/environment-setup/SKILL.md`](skills/environment-setup/SKILL.md).
4. **Machine-specific values live in `user_secrets.json`** at the root of the repo. It is
   **git-ignored — never commit it**, never paste its contents into a committed file, test,
   doc page or commit message. If it is missing, create it from the template in
   [`skills/environment-setup/SKILL.md`](skills/environment-setup/SKILL.md) §0.1 **and ask
   the user for the real values** (never guess a path).
5. **Submodules first.** `git submodule update --init --recursive` in `$OPEN_GATE_REPO`
   before building or running tests. Missing `opengate/tests/data` = most tests fail for
   the wrong reason.
6. **`--recurse-submodules` on clone**, `git lfs` must be installed (test data is large binary).
7. **Formatting is enforced** by `pre-commit` (black for Python, clang-format for C++,
   trailing whitespace). Run it before committing — see [`skills/code-style/SKILL.md`](skills/code-style/SKILL.md).
8. **Version bump = 3 places**: `VERSION` at root, and the release must republish both
   `opengate` and `opengate_core` (`opengate-core==10.1.1` is a hard pin in `setup.py`).
9. **Never commit generated artifacts**: `opengate/tests/output*/`, `opengate/tests/log/`,
   `dist/`, `build/`, `*.egg-info`, images/root files (see `.gitignore`).
10. **Do not let tests pollute the tree.** Running the suite can leave untracked files in
    the repository root (e.g. `simulation.json`, see B-006). Check `git status` after every
    run and remove them — never include them in a commit.
11. **Keep `skills/status/found-bugs.md` up to date** whenever you discover a bug you do
    not immediately fix, and `skills/status/task-list.md` when you plan/close work.
12. **Distinguish repository bugs from environment issues.** A wrong Geant4/ITK version, a
    stale compiled build or an un-activated venv is **not** a repo bug — fix the environment
    (see `skills/environment-setup`). Only log a repository bug once the environment has been
    proven correct.
13. **Do not run the whole suite casually**: it takes tens of minutes, downloads Geant4
    data on first run, and needs ~all cores. Use `--start_id/--end_id`/`-t` filters.
14. **Cite real evidence.** Do not claim a test passed unless you ran it (or read the CI
    result). Do not invent Geant4/actor parameter names — grep the code and docs first.

## 3. Skills index

Map of the `skills/` directory: [`skills/README.md`](skills/README.md).

| Skill | Use it when |
| --- | --- |
| [`skills/environment-setup/`](skills/environment-setup/SKILL.md) | You need a working virtual dev environment where **all tests** run (venv, Geant4/ITK, `pip install -e .`, optional extras). |
| [`skills/running-tests/`](skills/running-tests/SKILL.md) | You must run, filter, debug or interpret the test suite and its dashboard output. |
| [`skills/build-and-ci/`](skills/build-and-ci/SKILL.md) | You touch `core/`, wheels, `pyproject.toml`, or the GitHub Actions workflows. |
| [`skills/code-style/`](skills/code-style/SKILL.md) | Before every commit: formatting, naming, imports, docstrings. |
| [`skills/architecture/`](skills/architecture/SKILL.md) | You add/modify engines, managers, actors, sources, physics — the object lifecycle in GATE 10. |
| [`skills/documentation/`](skills/documentation/SKILL.md) | You add a user/developer guide page or build the Sphinx docs. |
| [`skills/engineering/`](skills/engineering/) | You are acting in a role: `python-gate-developer`, `geant4-physics-expert`, `simulation-debugger`, `test-writer`. |
| [`skills/status/`](skills/status/task-list.md) | You need the shared task list, the bug log, or the project status snapshot. |

## 4. Quick start (30-second version)

**Before anything else, get the machine's paths from `user_secrets.json`** (root of the
repo, git-ignored). If it does not exist, create it from the template in
[`skills/environment-setup/SKILL.md`](skills/environment-setup/SKILL.md) §0.1 and **ask the
user for the real values**. The environment **must be on non-volatile storage** (not
`/tmp`, a tmpfs, or a container layer): the C++ build and the downloaded Geant4 data take
minutes and GBs and must survive a reboot. **Reuse an existing environment if one already
works**; only create one when none does. `skills/environment-setup` §0 is machine-agnostic
— it never hard-codes a path.

```bash
# 0. load the user's paths from user_secrets.json (create it first if missing)
cd "$OPEN_GATE_REPO"
export OPEN_GATE_ENV="$(python3 -c 'import json;print(json.load(open("user_secrets.json"))["OPEN_GATE_ENV"])')"

# 1. submodules (git-lfs required)
git lfs install && git submodule update --init --recursive

# 2. environment — create only if no usable one exists (environment-setup §0.3–0.4)
uv venv "$OPEN_GATE_ENV"            # or: python3 -m venv "$OPEN_GATE_ENV"
source "$OPEN_GATE_ENV/bin/activate"

# 3. Python package, editable (uses the pip-provided opengate_core wheel)
python -m pip install -e .         # uv env: VIRTUAL_ENV="$OPEN_GATE_ENV" uv pip install -e .

# 4. smoke test — KEEP THE ENV ACTIVATED (the runner spawns `python <test>`),
#    and the -t path is relative to opengate/tests/src INCLUDING the subdirectory
#    (first run downloads Geant4 data on import — can take several minutes)
opengate_tests -t actors/test008_dose_actor.py
```

For anything involving `core/` (C++), Qt visualization, or a *reproducible* full-suite
run, follow [`skills/environment-setup/SKILL.md`](skills/environment-setup/SKILL.md)
which builds Geant4/ITK and `opengate_core` (ask the user for the deps prefix too).

## 5. Hierarchy of truth

When sources disagree, trust them in this order:

1. the code in `opengate/` and `core/` (runtime behaviour);
2. the test suite `opengate/tests/src/` (executable specification);
3. `.github/workflows/` (how the maintainers actually build & test);
4. `docs/source/` (may lag behind, especially `DesignGuidelines.md` which is marked **OBSOLETE**);
5. this file and `skills/` (may lag behind the code — fix them if you spot drift).

## 6. Git workflow — do this before starting any work

**`master` is read-only for agents.** Never commit, merge into, rebase onto, or push
`master`. The only thing an agent may do with it is **sync it from the remotes**, and every
change an agent makes must live on a **fresh branch based on the up-to-date local `master`**.

This repo has two remotes; check yours with `git remote -v`:

| Remote | Role |
| --- | --- |
| `origin` | the user's fork (where the agent's branches are pushed, only with user approval) |
| `opengate` | upstream `OpenGATE/opengate` (the source of truth) |

### 6.1 Sync (run at the start of every session and before creating a branch)

```bash
cd "$OPEN_GATE_REPO"

# 1. never work on master: get off it first if you are on it
[ "$(git branch --show-current)" = master ] && git switch -   # or: git switch <your-branch>

# 2. update the local master from the remotes (fast-forward only, no history rewrite)
git fetch origin
git fetch opengate
git switch master
git merge --ff-only origin/master      # local master must match origin/master
git merge --ff-only opengate/master    # and upstream (both should already be identical)
```

Verify all three are in sync — each count must be `0 0`:

```bash
git rev-list --left-right --count master...origin/master        # expect: 0  0
git rev-list --left-right --count master...opengate/master      # expect: 0  0
git rev-list --left-right --count origin/master...opengate/master  # expect: 0  0
```

If a `--ff-only` merge refuses, **stop and ask the user**: local `master` has diverged from
upstream, and resolving that is the user's decision (do not rebase or reset it yourself).

### 6.2 Create the branch — always fresh, always from master

```bash
git switch -c <type>-<short-topic> master     # e.g. fix-doseactor-scaling
```

Rules:

- **One branch per task**, cut from the current `master` tip. Never reuse an old branch for a
  new task, and never branch off another working branch.
- If you are already on a branch, verify it is based on the *current* master tip before adding
  commits:
  ```bash
  git merge-base --is-ancestor master HEAD && echo "based on master: OK"
  git log --oneline master..HEAD          # your commits — should be only your own work
  ```
- If `master` has advanced since you branched, **rebase onto it** rather than merging:
  ```bash
  git rebase master        # only if the branch has no shared/upstream commits, and only
                           # after telling the user — see golden rules
  ```
- **Never** `git push --force` to `master` or to a shared branch.
- Commit only what your task needs; stage explicitly (`git add <paths>`), never `git add -A`
  blindly.

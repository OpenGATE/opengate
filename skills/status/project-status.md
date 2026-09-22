# Project status snapshot

Rolling snapshot of what this repository *is* and in what state it is, so an agent can
orient itself without re-reading the tree. **Date every observation** — this file rots
faster than the code.

---

## Snapshot

- **Date of last update**: 2026-09-22
- **Version** (`VERSION`): 10.1.1
- **Python**: requires >= 3.9 in `pyproject.toml`; CI builds and tests **3.10 → 3.14**
  (`requires-python` and CI matrices disagree slightly — trust CI for what is exercised).
- **Native stack**: Geant4 `v11.4.2`, ITK `v5.4.4` (pinned in
  `.github/workflows/main.yml`). The developer guide still mentions ITK `v5.2.1` — stale.
- **Packages**: `opengate` (Python) + `opengate_core` (C++), the latter hard-pinned as
  `opengate-core==<VERSION>` in `setup.py`.
- **Platforms tested in CI**: `ubuntu-24.04` (+ `ubuntu-24.04-arm` on tag/schedule),
  `macos-15` (+ `macos-15-intel` on tag/schedule), `windows-2025`.
- **Known platform limitation**: on Windows, multithreading and Qt visualization are not
  available (`README.md`).

## Local reference environment (verified)

A working dev environment was exercised against this branch, so the following is measured,
not assumed. **Machine-specific absolute paths are not recorded here** — they belong in the
(sourced, git-ignored) `user_secrets.json`; see `skills/environment-setup` §0.

- **`user_secrets.json` at the repo root** holds `OPEN_GATE_REPO`, `OPEN_GATE_ENV`,
  `OPEN_GATE_DEPS`. It is git-ignored
  (`.gitignore` → "LOCAL MACHINE CONFIG"), so it is present on a developer's machine and
  absent from a fresh clone — agents must create it and ask the user for the values.
- **Environment type actually verified**: a **`uv`-created** venv (uv 0.12.10), CPython
  3.14.7. Its `pyvenv.cfg` recorded `version_info = 3.14.4` while the interpreter reported
  3.14.7; the runtime wins.
- **No `pip`** in a `uv` venv (`No module named pip`, no `bin/pip`): use `uv pip` with
  `VIRTUAL_ENV="$OPEN_GATE_ENV"`, or plain `python -m pip` on a stdlib venv.
- **Both packages editable** at `$OPEN_GATE_REPO` and `$OPEN_GATE_REPO/core`.
- **Geant4 now matches the pin**: the checkout was originally at `v11.4.0` (runner warned
  `Geant4 version is not ok`); it was updated to tag `v11.4.2`, rebuilt, and `opengate_core`
  relinked. The runner now reports **`Geant4 version is OK`**
  (`geant4-11-04-patch-02`, `G4VERSION_NUMBER 1142`). This was an environment issue (B-004),
  not a repository bug.
- **Geant4/ITK builds were reused, not rebuilt from scratch**: two pre-existing build trees
  under `$OPEN_GATE_DEPS`, which `core/config.json` does not pin (the file is absent, so
  `setup.py` passes empty `Geant4_DIR`/`ITK_DIR` and CMake resolves them via
  `CMAKE_PREFIX_PATH`). The from-scratch source build (`skills/environment-setup` §4.1–4.2)
  was therefore **not** exercised (T-003).
- **Geant4 data** downloads on the first `import opengate_core` into
  `core/opengate_core/geant4_data/` (6 archives, several minutes of apparent silence —
  not a hang).

## Build / test pipeline health

- CI entry point: `.github/workflows/main.yml` (push to `master`, PRs to `master`, tags,
  cron `0 0 * * 0,3`, manual dispatch).
- Wheel build: `.github/workflows/actions_build/action.yml` + three OS scripts; caches
  Geant4/ITK under `~/software`.
- Test run: `.github/workflows/actions_tests/action.yml` — installs the **built** wheels
  then runs `opengate_tests -r -s <sha>` (seeded random subset + last 10 tests).
- Results history: <https://opengate.github.io/opengate_tests_results> (aggregated from
  the uploaded `results_json-*` artifacts into `OpenGATE/opengate_tests_results`).
- Docs: Read the Docs builds from `docs/`; CI does not run on `docs/**` changes.

*Fill in the last observed CI status when you touch this file* (green/red per OS, link to
the run).

## Last observed local run

Not CI — a local run on the reference environment above, branch `agentic-skills`, after
rebuilding `opengate_core` (root cause in B-001):

### Full-suite baseline (368 tests, ~17.6 min)

Command: `opengate_tests` (no filters), commit `8f049324`, log kept outside the repo in a
non-volatile scratch dir. Result: **366/368 passed, 2 failed**.

| Metric | Value |
| --- | --- |
| Tests available / run / ignored | 458 / **368** / 90 |
| Passed | **366** |
| Failed | **2** |
| Dependency split | 354 in round 1, then 14 with mutual dependencies |
| Wall time | 17.6 min |
| Final summary line | `False` (i.e. not all passed) |
| Per-test logs | `opengate/tests/log/*.log` |

Failures:

| Test | Time | Note |
| --- | --- | --- |
| `geometry/test102_gammex467.py` | 44.1 s | geometry; plausibly Geant4-version sensitive |
| `geometry/test107_macaco1_mt.py` | 142.5 s | geometry + multithreaded |

**Validity caveat — now resolved.** This baseline was taken with **two** environment faults,
neither of which was a repository bug:

1. **Geant4 11.4.0** instead of the pinned 11.4.2 (B-004) — since fixed by rebuilding Geant4
   at v11.4.2 and relinking `opengate_core`; the runner now prints `Geant4 version is OK`.
2. **A stale `opengate/tests/data` submodule**, four commits behind the pointer recorded in
   this repo (B-009) — since fixed by `git submodule update --init`; the submodule is now at
   `9fabbdddf`.

**Both baseline failures were caused by fault 2 and are now green.** Re-run on the corrected
environment (Geant4 11.4.2, correct submodule):

```
Running: geometry/test102_gammex467.py    OK   18.1 s
Running: geometry/test107_macaco1_mt.py   OK   60.6 s
Summary pass: 2/2 passed the tests
True
```

Both logs end with “Great, tests are ok.”, including test107's physics assertion (FWHM within
tolerance). **No repository bug was found.** So the 366/368 baseline should be read as an
environment artifact, and a fresh full-suite run on the corrected tree is expected to be
green (T-014).

### Targeted verification runs

| Command | Result |
| --- | --- |
| `python -c "import opengate, opengate_core"` | clean; `opengate_core` resolves to `$OPEN_GATE_REPO/core/opengate_core` |
| `opengate_tests -t actors/test008_dose_actor.py` | **1/1 passed**, `True`, ~0.3 min |
| `opengate_tests -i 1 -e 12 -n 4` | **30/30 passed**, `True`, 2.2 min |
| `opengate_tests -l` | `114` (highest test id) |

The runner auto-runs `misc/test001_g4threevector.py` first to trigger data download, so
single-test runs report a 2-test progression (`30` for `-i 1 -e 12` includes it).
Two prerequisites were required and are easy to get wrong — the venv must be **activated**
(B-002) and `opengate_core` must be **freshly compiled** (B-001).

Not exercised locally: the torch / `gaga_phsp` / `pytomography` tests (T-009), Windows/macOS,
and the from-scratch source build (T-003).

## Test suite shape

- Location: `opengate/tests/src/{actors,advanced_tests,chemistry,external,geometry,misc,physics,source}`.
- Runner: `opengate_tests` (see `skills/running-tests`). Not pytest.
- **Size (measured)**: 458 `testNNN*.py` files; the runner reports **368 to run and 90
  ignored** (ignore patterns: `_helpers`, `wip`, `debug`, `> <id>`, …), plus 11 skipped for
  missing `torch`. Of the 368 available, a 30-test slice passed **30/30**.
- Binary test data: `opengate/tests/data` submodule on gitlab.in2p3.fr (git-lfs),
  **75 entries** when populated.
- Optional-dependency tests: some need `torch`, `gaga-phsp`, `garf`, `pytomography`,
  `hist` — CI installs them; the reference env does not.
- Per-test logs: `opengate/tests/log/<test name>.log` (the fastest place to read a failure).
- Dashboard JSON: `opengate/tests/output_dashboard/dashboard_output_<sys.platform>_<maj>.<min>.json`
  — e.g. `dashboard_output_linux_3.14.json` on the reference env. Values are `[""]` until
  the test has run; that empty status is what `opengate_tests -f` uses to re-run failures.
- **The runner does not validate the environment**: `check_environment()`
  (`opengate/bin/opengate_tests_helpers.py`) only warns on a Geant4 version mismatch and
  checks the data folder. A broken `opengate_core` (B-001) or an un-activated venv (B-002)
  produces hundreds of identical failures instead of one clear error.

## Documentation state

- Sphinx sources under `docs/source/{user_guide,developer_guide}`; themed with PDJ.
- `user_guide_reference_*.rst` = exhaustive references; `user_guide_*.rst` = narratives.
- Known stale spots: `DesignGuidelines.md` (marked **OBSOLETE**), the ITK version in
  `developer_guide_installation.rst`, and `opengate/tests/readme.md` (says
  "documentation in progress").

## Agent-facing assets (this directory)

| Asset | Purpose |
| --- | --- |
| `AGENTS.md` | entry point, golden rules, skills index |
| `user_secrets.json` (root, **git-ignored**) | per-machine paths: `OPEN_GATE_REPO`, `OPEN_GATE_ENV`, `OPEN_GATE_DEPS` |
| `skills/README.md` | map of the skills directory, role-vs-task split |
| `skills/environment-setup` | how to obtain a virtual dev env (reuse-first, non-volatile) where **all** tests run |
| `skills/running-tests` | the `opengate_tests` runner, filters, dashboard |
| `skills/build-and-ci` | wheels, CI topology, version bump |
| `skills/code-style` | pre-commit / black / clang-format, conventions |
| `skills/architecture` | managers/engines/actors/sources lifecycle |
| `skills/documentation` | Sphinx pages and local build |
| `skills/engineering/python-gate-developer` | role: Python API design, C++ boundary, serialisation |
| `skills/engineering/geant4-physics-expert` | role: physics lists, cuts, statistics, realism |
| `skills/engineering/simulation-debugger` | role: triage, reproduction, lifecycle-localised diagnosis |
| `skills/engineering/test-writer` | role: test placement, assertions, tolerances |
| `skills/status/` | this snapshot, `task-list.md`, `found-bugs.md` |

## Open questions / risks to watch

- The skill documents describe the tree at the commit they were written against; CI keys
  and runner options drift. If a command in `skills/` fails, fix the skill as part of the
  same change (`AGENTS.md` §5).
- `user_secrets.json` is git-ignored, so a fresh clone **has no paths at all**: the first
  agent on a machine must create it and ask the user. Treat "file missing" as normal, and
  treat "committed" as a security incident (remove from the index immediately).
- `requires-python = ">=3.9"` vs. CI floor 3.10 vs. `README.md` claiming 3.10+: keep an
  eye on which one the packaging actually honours.
- The `docs/**` path filter means documentation regressions are only caught by Read the
  Docs builds, not by the main CI.

## Update protocol

1. Set the date line when you edit.
2. Change **facts**, not opinions; keep each line verifiable from a file or a CI run.
3. If a statement stops being true, delete it rather than leaving a stale note.
4. Log anything you discover but do not fix in [`found-bugs.md`](found-bugs.md) and
   [`task-list.md`](task-list.md).
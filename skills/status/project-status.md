# Project status snapshot

Rolling snapshot of what this repository *is* and in what state it is, so an agent can
orient itself without re-reading the tree. **Date every observation** — this file rots
faster than the code.

---

## Snapshot

- **Date of last update**: *(set when you edit this file)*
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

## Test suite shape

- Location: `opengate/tests/src/{actors,advanced_tests,chemistry,external,geometry,misc,physics,source}`.
- Runner: `opengate_tests` (see `skills/running-tests`). Not pytest.
- Binary test data: `opengate/tests/data` submodule on gitlab.in2p3.fr (git-lfs).
- Optional-dependency tests: some need `torch`, `gaga-phsp`, `garf`, `pytomography`,
  `hist` — CI installs them; a minimal local env does not.
- Dashboard JSON: `opengate/tests/output_dashboard/dashboard_output*.json`; empty status
  means "never run", which `opengate_tests -f` uses to re-run failures.

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
| `skills/environment-setup` | how to build a virtual dev env where **all** tests run |
| `skills/running-tests` | the `opengate_tests` runner, filters, dashboard |
| `skills/build-and-ci` | wheels, CI topology, version bump |
| `skills/code-style` | pre-commit / black / clang-format, conventions |
| `skills/architecture` | managers/engines/actors/sources lifecycle |
| `skills/documentation` | Sphinx pages and local build |
| `skills/status/` | this snapshot, `task-list.md`, `found-bugs.md` |

## Open questions / risks to watch

- The skill documents describe the tree at the commit they were written against; CI keys
  and runner options drift. If a command in `skills/` fails, fix the skill as part of the
  same change (`AGENTS.md` §5).
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
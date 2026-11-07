# Skill: `environment-setup/build-and-ci`

**Goal:** know how OpenGATE is **built, packaged, released and tested in CI** — and reproduce that
process locally when a failure is CI-only.

This is the deep-dive companion to [`SKILL.md`](SKILL.md). It is the single owner of the
*build/release/CI* knowledge. If you only need a working environment, you do **not** need this
file — `SKILL.md` §0–§5 are enough.

Ownership boundaries:

| Topic | Owner |
| --- | --- |
| How to *compile* Geant4, ITK and `opengate_core` | [`geant4-itk.md`](geant4-itk.md) |
| How to *package*, *release* and *test in CI* — and the packaging consequences of touching `core/` | **this file** |
| The runner, its options, its exit code | [`../running-tests/SKILL.md`](../running-tests/SKILL.md) |

---

## 1. Two packages that must move together

The repository ships **two** packages:

| Package | Source | Contents |
| --- | --- | --- |
| `opengate` | `opengate/`, `pyproject.toml`, `setup.py` | pure Python |
| `opengate_core` | `core/`, `core/setup.py` | C++ (pybind11) binding Geant4 + ITK, **shipped as a compiled wheel** |

`opengate` has a **hard pin** on its partner: `setup.py:15` sets
`install_requires=["opengate-core==" + version]`, where `version` is read from `VERSION`
(`core/setup.py:30` reads the same file). Consequence: **a version bump means republishing
both packages**, and any mismatch installs the wrong C++ layer.

## 2. CI topology — read `.github/workflows/main.yml`

The orchestrator is `main.yml`; the reusable pieces are composite actions. **Check the job
names in the file rather than trusting a summary** — they have changed before (B-005 was
caused by code reading a job name that no longer exists).

Workflow-level pins (top of `main.yml`, in the `env:` block — this is the source of truth):

```yaml
env:
  GEANT4_VERSION: 'v11.4.2'
  ITK_VERSION: 'v5.4.4'
```

| Job | Purpose |
| --- | --- |
| `build_opengate_wheel` | builds the pure-Python `opengate` wheel (one Python version is enough). |
| `build_opengate_core_wheel_pr` | builds the `opengate_core` wheel for the PR matrix (docker-based on Linux). |
| `build_opengate_core_wheel_ci_or_tag` | the CI/tag build of `opengate_core`. |
| `build_opengate_core_novis_wheel` | the no-visualisation variant (`opengate-core-novis`). |
| `publish_wheel` | splits and publishes wheels to PyPI — **only on a tag push**. |
| `test_wheel_pr` | installs the **built wheels** and runs the suite (see §4). |
| `publish_test` | publishes the results dashboard (master only). |

Triggers: push/PR to `master` (PRs are cancelled in progress if superseded), a
**scheduled** run (`cron '0 0 * * 0,3'`, i.e. Sun/Wed), and `workflow_dispatch`.
**`docs/**` is in `paths-ignore`** — a docs-only change does not run CI.

Helper files you may need to touch, all under `.github/workflows/`:
`actions_build/` (composite build action + `ci_build_wheel_{ubuntu,macos,windows}.sh`),
`actions_tests/action.yml`, the `Dockerfile_opengate_core*` images,
`createWheelLinux*.sh`, `delocateWindows.py`, `redoQt5LibsMac.py`.

## 3. Releasing a version — the three steps

`VERSION` at the repo root is the **single source of truth**; both `setup.py` files read it.
To release:

1. **Bump `VERSION`** (e.g. `10.1.1` → `10.1.2`).
2. **Republish both packages.** `opengate` pins `opengate-core==<VERSION>`
   (`setup.py:15`), so publishing `opengate` alone yields an unsatisfiable requirement —
   CI would install nothing or fall back to a stale wheel.
3. **Tag the release.** `publish_wheel` only pushes to PyPI on
   `github.event.ref` starting with `refs/tags/`; a plain branch push builds but does not
   publish.

Verify before tagging:

```bash
cd "$OPEN_GATE_REPO"
grep -rn "opengate-core==" setup.py        # the pin must match VERSION
diff <(cat VERSION) <(cd core && python -c "print(open('../VERSION').read()[:-1])") && echo "VERSION consistent"
```

Do **not** rename or remove a public parameter as part of a release without a deprecation path
(see [`engineering/python-gate-developer.md`](../engineering/python-gate-developer.md) §3).

## 4. What CI actually does when it tests

This is the part most often got wrong locally, because CI does **not** test an editable
install — it tests the **wheels**:

- `actions_tests/action.yml` deletes the workspace, downloads the artifacts, and installs
  `dist/opengate_core-*.whl` then `dist/opengate-*.whl`. A bug that only exists in the wheel
  (missing file in `MANIFEST`, a stray import) therefore appears **only in CI**.
- Matrix: `{ubuntu-24.04, macos-15, windows-2025} × Python 3.10–3.14`, excluding macOS and
  Windows on 3.10.
- Optional extras are installed explicitly: `torch`, `SimpleITK`, `gaga_phsp>=0.7.6`,
  `pytomography`, `hist`. A test that needs them passes in CI and is skipped locally
  (`SKILL.md` §5).
- On Linux/Windows the library path is extended via
  `opengate_library_path.py -p site_packages` → `opengate_core.libs`.
- **The pass criterion is the last line of the runner output being exactly `True`** — the job
  fails otherwise. This is why every `opengate_tests` invocation must end with `True`;
  see [`running-tests/SKILL.md`](../running-tests/SKILL.md).
- Test selection: scheduled runs execute **everything**; push/PR runs use
  `opengate_tests -r -s $sha` — `-r` runs **the last 10 tests plus 1/4 of the others, chosen
  randomly** (see `opengate/bin/opengate_tests.py`), so a PR is *not* a full-suite guarantee.
  `-s` seeds that random choice so a CI run is reproducible.
- The `opengate` wheel is built with `opengate/tests/data` **removed** and replaced by a
  gitlink (`cp .git/modules/gam-tests/data/HEAD opengate/tests/`), so the binary test data is
  not shipped in the wheel.

## 5. Reproducing CI locally

CI installs wheels into a scratch environment; do the same rather than testing your editable
install — a wheel-only bug cannot reproduce otherwise.

```bash
cd "$OPEN_GATE_REPO" && source "$OPEN_GATE_ENV/bin/activate"   # activation is required (SKILL.md §3.1)
python -m build                                                 # -> dist/
pip install dist/opengate_core-*.whl dist/opengate-*.whl
export GIT_SSL_NO_VERIFY=1
opengate_tests -r -s localsha                                   # same shape as the PR job
```

`-s` is only a seed for the random test choice; CI passes a value derived from the commit SHA
and the OS/Python tag.

Caveats:

- This **replaces your editable installs with wheels** — do it in a scratch environment, not
  the one you develop in, or you will silently lose the source build.
- The wheel pulls `opengate-core==<VERSION>` from PyPI if your local wheel is not visible;
  install the locally built `opengate_core` wheel **first** (as above).
- Full-suite parity means installing the optional extras of `SKILL.md` §5.
- A CI-only failure is usually one of: a file missing from the wheel, an extra only CI has,
  the `output_dashboard` path, or the platform's library path.

## 6. Packaging consequences of touching `core/`

The authoritative **build** procedure is [`geant4-itk.md`](geant4-itk.md) §4 (Geant4/ITK,
`core/config.json`, incremental rebuild). Only the packaging/CI consequences belong here:

- Geant4/ITK are located via `core/config.json` (`G4INSTALL`, `ITKDIR`; git-ignored) or
  through `CMAKE_PREFIX_PATH` when the file is absent. The environment also reads the
  `G4INSTALL`/`ITKDIR` variables, but `config.json` **wins** when present.
- Parallelism is `os.cpu_count()`, overridable with `OPEN_GATE_BUILD_JOBS`
  (B-007 fixed the old hard-coded `-j4`).
- **An editable install never rebuilds the `.so`** — the failure is a misleading
  `AttributeError: module 'opengate_core' has no attribute 'Gate…'`
  ([`geant4-itk.md`](geant4-itk.md) §7). Rebuild before concluding anything about a C++ change.
- A new binding must be registered in `core/opengate_core/opengate_core.cpp` **and** the
  extension rebuilt, or it does not exist at runtime.

## 7. Editing the workflows safely

- **Change the pin in one place.** `GEANT4_VERSION` / `ITK_VERSION` live in the workflow-level
  `env:` block of `main.yml`; the build scripts and the test action consume them. Do not
  hard-code a second copy.
- **Keep job names and the code that reads them in sync.** B-005 is exactly this defect:
  `get_required_g4_version()` in `opengate/bin/opengate_tests_helpers.py` indexes
  `jobs.build_wheel`, a job that does not exist, and silently falls back to a literal.
  If you rename a job, grep the Python for it.
- **CI validates against a hard-coded fallback today**, so a pin bump can silently stop being
  enforced until B-005 is fixed — verify by reading `main.yml` yourself.
- **Secrets are needed for publish** (`PYPI_OPENGATE_CORE*`); a fork's PR cannot publish, and
  publication only happens on tags (§3).
- Local runs cannot reproduce the docker-based Linux build
  (`Dockerfile_opengate_core{,_arm64,_novis}`) — treat a Linux-wheel-specific failure as
  needing a CI run, not a local guess.
- Keep `paths-ignore: docs/**` in mind: a docs-only PR does not exercise the build.

## 8. Definition of done

- [ ] The job names and pins you relied on were read from `main.yml`, not recalled.
- [ ] A version bump touched `VERSION` **and** both packages, and the `opengate-core==` pin matches.
- [ ] The release is tagged (`refs/tags/…`), not just pushed on a branch.
- [ ] A CI-only failure was reproduced with **wheels** in a scratch environment (§5), not with an
      editable install.
- [ ] Any `core/` change was rebuilt before the packaging conclusion was drawn
      ([`geant4-itk.md`](geant4-itk.md) §7).
- [ ] Workflow edits kept a single source for each pin and left job names greppable by the Python
      that reads them.

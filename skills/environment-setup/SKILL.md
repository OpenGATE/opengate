# Skill: environment-setup

**Goal:** produce a virtual development environment in which the *whole* OpenGATE test
suite can run, and prove it works before you change anything.

Do not skip the verification step. A tree that imports `opengate` but runs against a
stale pip `opengate_core` wheel produces "wrong but plausible" failures that will waste
hours.

---

## 1. Decide which install you need

| Situation | Install path |
| --- | --- |
| Only touching Python (`opengate/**`) | **Fast path** (§3): editable pip install, pip-provided `opengate_core` wheel. |
| Touching `core/**` (C++, bindings, Geant4/ITK behavior) | **Full path** (§4): build Geant4, ITK and `opengate_core` from source. |
| Reproducing CI exactly / Qt visualization / debugging native crashes | **Full path** (§4) + the CI-matching notes (§6). |

Rule of thumb: if `git diff --name-only master` shows anything under `core/`, you need
the full path. Otherwise the fast path is enough.

## 2. Preconditions (always)

```bash
# git-lfs is REQUIRED: opengate/tests/data is a binary submodule
git lfs install
git clone --recurse-submodules https://github.com/OpenGATE/opengate
cd opengate

# or, in an existing clone:
git submodule update --init --recursive
```

If the submodule fetch fails behind a proxy/TLS interception:

```bash
export GIT_SSL_NO_VERIFY=1     # CI itself does this (see .github/workflows/main.yml)
```

Check the data submodule is really populated before running anything:

```bash
ls opengate/tests/data | head     # must not be empty
ls core/external/pybind11 | head  # must not be empty
ls core/external/fmt | head       # must not be empty
```

## 3. Fast path — Python development

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip

# installs opengate + pulls opengate-core==$(cat VERSION) from PyPI
python -m pip install -e .
```

The pip `opengate_core` wheel already contains Geant4 and ITK, so this is enough for
almost all Python-level work.

Smoke test (first run downloads Geant4 data — allow several minutes):

```bash
opengate_tests -t source/test008_dose_actor.py
```

`opengate_info` prints the resolver's view of your environment; use it when something
looks inconsistent:

```bash
opengate_info
```

## 4. Full path — build Geant4, ITK and `opengate_core`

You need: a C++17 compiler, CMake, ~30 GB of disk, and patience (parallel `make -j N`).
Optional: Qt6 (install it **before** Geant4 if you want `opengate_visu`).

Pick a prefix, e.g. `$HOME/software`. The CI caches exactly `~/software`
(`.github/workflows/actions_build/action.yml`), and the helper script expects this layout.

### 4.1 Geant4 `v11.4.2`

```bash
git clone --branch v11.4.2 https://github.com/Geant4/geant4.git --depth 1
mkdir geant4.11-build && cd geant4.11-build
cmake -DCMAKE_CXX_FLAGS=-std=c++17 \
      -DGEANT4_INSTALL_DATA=ON \
      -DGEANT4_INSTALL_DATADIR=$HOME/software/geant4/data \
      -DGEANT4_USE_QT=ON \
      -DGEANT4_USE_OPENGL_X11=ON \
      -DGEANT4_USE_QT_QT6=ON \
      -DGEANT4_BUILD_MULTITHREADED=ON \
      -DGEANT4_BUILD_TLS_MODEL=global-dynamic \
      ../geant4
make -j $(nproc)
```

Set `GEANT4_USE_QT` and `GEANT4_USE_OPENGL_X11` to `OFF` if Qt is not installed.
`GEANT4_BUILD_TLS_MODEL=global-dynamic` avoids the `cannot allocate memory in static
TLS block` error on some Linux distros at a ~10 % speed cost.

### 4.2 ITK

```bash
git clone --branch v5.2.1 https://github.com/InsightSoftwareConsortium/ITK.git --depth 1
mkdir itk-build && cd itk-build
cmake -DCMAKE_CXX_FLAGS=-std=c++17 -DBUILD_TESTING=OFF ../ITK
make -j $(nproc)
```

Note: the CI pins ITK `v5.4.4` (`env.ITK_VERSION` in `main.yml`); the developer guide
still shows `v5.2.1`. Either works locally — use the CI version if you need to match CI.

### 4.3 `opengate_core` (C++ bindings)

```bash
cd <path-to-opengate>/core
export CMAKE_PREFIX_PATH=<path-to>/geant4.11-build/:<path-to>/itk-build/:${CMAKE_PREFIX_PATH}
python -m pip install -v -e .
```

On Windows use `;` as the `CMAKE_PREFIX_PATH` separator, not `:`.

This runs CMake and compiles the module in place; the build tree lands in `core/build/`.

### 4.4 `opengate` (Python)

```bash
cd <path-to-opengate>
python -m pip install -v -e .
```

Because `opengate_core` is already installed from source, pip will not pull the wheel.
If pip *does* try to install `opengate-core==$(cat VERSION)` from PyPI, your editable
`opengate_core` is not visible in this environment — fix that instead of letting pip
overwrite it.

### 4.5 TLS workaround (only if §4.1 was built without `global-dynamic`)

```bash
export LD_PRELOAD=<path-to>/libG4processes.so:<path-to>/libG4geometry.so:${LD_PRELOAD}
```

## 5. Optional extras some tests need

Several tests fail at import time without these; that is expected and not a regression.

```bash
python -m pip install torch            # CPU wheel is enough
# Linux CPU-only, lighter:
# python -m pip install torch --extra-index-url https://download.pytorch.org/whl/cpu
python -m pip install gaga-phsp        # >=0.7.6 in CI
python -m pip install garf
python -m pip install pytomography hist
```

Additionally CI installs `SimpleITK` explicitly and, on Linux/Windows, extends the
library path using the helper script:

```bash
path=$(opengate_library_path.py -p site_packages)
export LD_LIBRARY_PATH="${path}/opengate_core.libs":${LD_LIBRARY_PATH}   # Linux
export PATH="${path}\\opengate_core.libs":${PATH}                        # Windows (git-bash)
```

## 6. Reproducing CI locally

CI (`.github/workflows/main.yml`) builds wheels on `ubuntu-24.04`, `macos-15`,
`windows-2025` for Python 3.10–3.14, then *installs the built wheels* and runs
`opengate_tests -r -s <sha>` (random subset + last 10 tests) inside
`.github/workflows/actions_tests/action.yml`.

To mimic it:

```bash
python -m build                       # in the repo root -> dist/
pip install dist/opengate_core-*.whl dist/opengate-*.whl
export GIT_SSL_NO_VERIFY=1
opengate_tests -r -s localsha
```

Remember the CI deletes `opengate/tests/data` before building the `opengate` wheel and
replaces it with a gitlink (`cp .git/modules/gam-tests/data/HEAD opengate/tests/`).

## 7. Verification checklist (do this before reporting anything)

```bash
python -c "import opengate, opengate_core; print(opengate.__file__); print(opengate_core.__file__)"
python -c "import opengate as gate; print(gate.__version__ if hasattr(gate,'__version__') else 'n/a')"
opengate_tests -t source/test008_dose_actor.py   # one fast, representative test
```

- [ ] `opengate.__file__` points into **this** working tree.
- [ ] `opengate_core.__file__` matches the install path you intended (source build vs wheel).
- [ ] `ls opengate/tests/data` is non-empty.
- [ ] One targeted test passes.
- [ ] `python -m pip freeze` recorded in your report if you are filing a bug.

## 8. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `ModuleNotFoundError: opengate_core` | You are in the wrong venv, or the C++ build failed. Re-run `pip install -e .` in `core/` and read the CMake output. |
| CMake cannot find Geant4/ITK | `CMAKE_PREFIX_PATH` unset or wrong separator (`:` on Linux/macOS, `;` on Windows). |
| `cannot allocate memory in static TLS block` | See §4.5, or rebuild Geant4 with `GEANT4_BUILD_TLS_MODEL=global-dynamic`. |
| Tests fail en masse with missing files | `opengate/tests/data` submodule not initialized (§2). |
| Download of Geant4/test data fails | `export GIT_SSL_NO_VERIFY=1` and retry. |
| Random test failures / crashes under load | CI runs many processes; reduce with `opengate_tests -n 4`. |
| Stale `*.so` after pulling C++ changes | Rebuild: `cd core && pip install -v -e .`; delete `core/build/` if inconsistent. |

## 9. Clean-up / from-scratch reset

```bash
deactivate && rm -rf .venv
cd core && rm -rf build CMakeFiles CMakeCache.txt
git submodule update --init --recursive
cd .. && rm -rf opengate/tests/output* opengate/tests/log
```

Never commit any of the removed paths — see `.gitignore`.
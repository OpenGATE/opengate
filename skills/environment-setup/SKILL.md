# Skill: environment-setup

**Goal:** obtain a virtual development environment in which the *whole* OpenGATE test
suite can run, and prove it works before you change anything.

Do not skip the verification step. A tree that imports `opengate` but runs against a
stale compiled `opengate_core` produces "wrong but plausible" failures that waste hours.

---

## 0. Two paths must come from the user (never invent them)

This document is deliberately **machine-agnostic**: no absolute path, no username, no
drive letter. The per-machine values live in **`user_secrets.json` at the root of the
repository**, which is **git-ignored and never committed**.

### 0.1 Read — or create — `user_secrets.json`

**Always do this first.** The file is expected at `$OPEN_GATE_REPO/user_secrets.json`:

```bash
cd "$OPEN_GATE_REPO"
cat user_secrets.json 2>/dev/null || echo "MISSING: user_secrets.json"
```

If it does **not** exist, **create it from the template below and then ask the user for the
real values** — placeholder values are not usable, and you must not guess a path. If it
exists but still contains `CHANGE_ME`, ask the user for the missing entries before
installing or building anything.

The file is JSON with these keys:

| Key | What it is | Rules |
| --- | --- | --- |
| `OPEN_GATE_REPO` | Absolute path of the OpenGATE working tree (the directory containing `VERSION`, `pyproject.toml`, `opengate/`, `core/`). | Must be a clone of this repository — often the current working directory. Must **not** be inside the environment. |
| `OPEN_GATE_ENV` | Absolute path of the Python environment used to build and test. | **Must be on non-volatile storage** — a real disk, not `/tmp`, `/run`, a tmpfs, an overlay, or a container's ephemeral layer, because a multi-minute C++ build and the downloaded Geant4 data (GBs) must survive a reboot/session. |
| `OPEN_GATE_DEPS` | Where Geant4 and ITK are built or installed, in `<prefix>/geant4.11-build` and `<prefix>/itk-build` subdirectories. | Only needed for the full C++ path (§4). Also non-volatile: these are ~10 GB builds. |

Template to create (the real file must contain the user's actual paths):

```json
{
  "OPEN_GATE_REPO": "/absolute/path/to/this/opengate/clone",
  "OPEN_GATE_ENV": "/absolute/non-volatile/path/to/the/venv",
  "OPEN_GATE_DEPS": "/absolute/non-volatile/path/to/geant4-and-itk-builds"
}
```

**Never commit it** and never copy its contents into a committed file, a test, a doc page
or a commit message. `.gitignore` already excludes `user_secrets.json` and
`user_secrets.*.json`; verify with `git check-ignore -v user_secrets.json`. If it is ever
staged, remove it from the index (`git rm --cached user_secrets.json`) and tell the user.

### 0.2 Load it into the shell session

**Everything below uses these variables.** Export them from the file so no command ever
hard-codes a path:

```bash
cd "$OPEN_GATE_REPO"   # or: export OPEN_GATE_REPO=<path> if you are not there yet
export OPEN_GATE_ENV="$(python3 -c 'import json;print(json.load(open("user_secrets.json"))["OPEN_GATE_ENV"])')"
export OPEN_GATE_DEPS="$(python3 -c 'import json;print(json.load(open("user_secrets.json")).get("OPEN_GATE_DEPS",""))')"
```

Verify the values make sense before using them — an empty, placeholder, or relative value
means the file is incomplete and you must go back to the user:

```bash
echo "repo=$OPEN_GATE_REPO"; echo "env=$OPEN_GATE_ENV"; echo "deps=$OPEN_GATE_DEPS"
[ -d "$OPEN_GATE_REPO/.git" ] || echo "OPEN_GATE_REPO does not look like a git clone"
case "$OPEN_GATE_ENV" in ""|*CHANGE_ME*) echo "OPEN_GATE_ENV is not set by the user";; esac
df -h "$OPEN_GATE_ENV" 2>/dev/null   # must show a real filesystem, not tmpfs
```

Windows PowerShell equivalent:

```powershell
$s = Get-Content user_secrets.json | ConvertFrom-Json
$env:OPEN_GATE_REPO = $s.OPEN_GATE_REPO
$env:OPEN_GATE_ENV  = $s.OPEN_GATE_ENV
$env:OPEN_GATE_DEPS = $s.OPEN_GATE_DEPS
```

### 0.3 Reuse an existing environment before creating one

**Prefer reusing what is already on the machine.** A suitable environment may exist —
created by the user, by a previous session, or by `uv`. Detect it, validate it (§7), and
only build a new one if validation fails.

Ask the user first, then look:

```bash
# candidates the user may name, or that may already be set in the shell
env | grep -iE 'virtual_env|conda|open_gate'            # already-active environment?
ls -d "$OPEN_GATE_REPO/.venv" 2>/dev/null                # repo-local venv, if allowed
find "$HOME" -maxdepth 3 -name 'pyvenv.cfg' 2>/dev/null  # venvs near the user's home
```

Identify what a candidate *is* before trusting it (run its interpreter directly):

```bash
"$CANDIDATE/bin/python" -c 'import sys; print(sys.executable, sys.version)'
"$CANDIDATE/bin/python" -c 'import opengate, opengate_core; print(opengate.__file__); print(opengate_core.__file__)'
"$CANDIDATE/bin/uv" --version 2>/dev/null; "$CANDIDATE/bin/python" -m pip --version 2>/dev/null
```

Then answer three questions:

1. **Is it non-volatile?** Reject a path under `/tmp`, `/var/tmp`, `/run`, `/dev/shm`, a
   `tmpfs` mount, or inside the C++ build tree. Verify with `df -h "$CANDIDATE"`: if the
   `Filesystem`/`Mounted on` points at `tmpfs`, or `df` reports a tiny size, reject it.
2. **Is it for *this* repo?** `opengate.__file__` must resolve inside `$OPEN_GATE_REPO`
   (an editable install) — or the user must confirm a wheel install is intended.
3. **Is it consistent?** Both packages present, same version as `VERSION`, and the
   compiled `opengate_core` newer than the C++ sources (§3.3, §4.6).

If it passes all three, set `OPEN_GATE_ENV` to it and skip to §6/§7. If it fails, tell the
user *which* check failed (and log it in `skills/status/found-bugs.md` if it looks like a
real defect) before rebuilding.

### 0.4 Creating an environment when none is reusable

Create it **at the user-provided path**, on non-volatile storage. Two supported tools:

```bash
# with uv (preferred if available: no pip, fast resolution)
uv venv "$OPEN_GATE_ENV"

# or with the stdlib
python3 -m venv "$OPEN_GATE_ENV"
```

If the user has not provided a path, propose one **outside** `/tmp` — for instance next to
the repository or under the user's home (`$HOME/pyenv/opengate`) — and **confirm it before
creating anything**. Never create an environment, a Geant4/ITK build, or the test-data
download inside a volatile directory.

A `uv`-created environment has **no `pip`** (see §3.1); note which tool you used, since
every install command below has two forms.

---

## 1. Decide which install you need

| Situation | Install path |
| --- | --- |
| Only touching Python (`opengate/**`) | **Fast path** (§3): editable install, `opengate_core` from PyPI wheel or reused build. |
| Touching `core/**` (C++, bindings, Geant4/ITK behavior) | **Full path** (§4): build Geant4, ITK and `opengate_core`. |
| Reproducing CI exactly / Qt visualization / debugging native crashes | **Full path** (§4) + the CI-matching notes (§5). |

Rule of thumb: if `git diff --name-only master` shows anything under `core/`, you need
the full path. Otherwise the fast path is enough.

## 2. Preconditions (always)

Work in `$OPEN_GATE_REPO` (from `user_secrets.json`, §0.2). If the tree is not cloned yet,
clone it **to a non-volatile location the user agrees with** — the secrets file lives
*inside* the repo, so on a fresh clone you create it there and ask the user for the values:

```bash
cd "$OPEN_GATE_REPO"          # the existing clone

# git-lfs is REQUIRED: opengate/tests/data is a binary submodule
git lfs install
git submodule update --init --recursive
```

If the submodule fetch fails behind a proxy/TLS interception:

```bash
export GIT_SSL_NO_VERIFY=1     # CI itself does this (see .github/workflows/main.yml)
```

Check the data submodule is really populated before running anything:

```bash
ls "$OPEN_GATE_REPO/opengate/tests/data" | head     # must not be empty
ls "$OPEN_GATE_REPO/core/external/pybind11" | head  # must not be empty
ls "$OPEN_GATE_REPO/core/external/fmt" | head       # must not be empty
```

## 3. Fast path — Python development


```bash
python3 -m venv "$OPEN_GATE_ENV"          # created in §0.4 if it did not exist
source "$OPEN_GATE_ENV/bin/activate"      # Windows: "$OPEN_GATE_ENV/Scripts/activate"
python -m pip install --upgrade pip

cd "$OPEN_GATE_REPO"
# installs opengate + pulls opengate-core==$(cat VERSION) from PyPI
python -m pip install -e .
```

The `opengate_core` wheel already contains Geant4 and ITK, so this is enough for almost
all Python-level work. If `$OPEN_GATE_ENV` was created with `uv`, use the `uv` form below.

### 3.1 `uv`-managed environments

A venv created by **`uv`** has **no `pip` module** — `python -m pip ...` fails with
`No module named pip`, and there is no `bin/pip` either. Use `uv pip` against the
environment instead:

```bash
VIRTUAL_ENV="$OPEN_GATE_ENV" uv pip install -e .        # from $OPEN_GATE_REPO
VIRTUAL_ENV="$OPEN_GATE_ENV" uv pip list | grep -i opengate
```

Or activate it and use `uv pip` without `VIRTUAL_ENV`:

```bash
source "$OPEN_GATE_ENV/bin/activate"
uv pip install -e .
```

Detect which tool made an environment you are **reusing** (§0.3):

```bash
"$OPEN_GATE_ENV/bin/python" -m pip --version      # pip present  -> pip form
ls "$OPEN_GATE_ENV/bin/pip" 2>/dev/null; grep -i uv "$OPEN_GATE_ENV/pyvenv.cfg"  # uv form
```

**You must activate the environment (or export `PATH`), not just call its interpreter by
absolute path.** `opengate_tests` launches each test as the literal shell command
`python <test path>` (`opengate/bin/opengate_tests_helpers.py`, `run_one_test_case`), so
an un-activated venv makes the subprocess resolve `python` to the system interpreter and
every test dies with `ModuleNotFoundError: No module named 'opengate'` — while the
runner itself imported `opengate` fine. Always `source "$OPEN_GATE_ENV/bin/activate"`
first. (Logged as B-002 in `skills/status/found-bugs.md`.)

### 3.2 Smoke test

First run downloads Geant4 data — allow several minutes. The download is triggered on
**first `import opengate_core`** (so even `python -c "import opengate"` blocks while
`G4*.tar.gz` archives are fetched into `core/opengate_core/geant4_data/`); only then is
there output. Do not mistake this silence for a hang.

```bash
source "$OPEN_GATE_ENV/bin/activate"
cd "$OPEN_GATE_REPO"
opengate_tests -t actors/test008_dose_actor.py    # path relative to opengate/tests/src
```

Test paths passed to `-t` are relative to `opengate/tests/src` **including the
subdirectory**, e.g. `actors/test008_dose_actor.py`, `source/test010_generic_source.py`.
A path that does not exist under `src/` is a fatal error
(`Explicit test paths must point inside the OpenGATE tests/src folder`), so check with
`find "$OPEN_GATE_REPO/opengate/tests/src" -name 'testNNN*.py'` first. Verified: this
command passes (`1/1`) on a correctly built environment.

`opengate_info` prints resolver information (Geant4 version, data paths). Note it
**imports `opengate`**, so it fails with the same stale-`opengate_core` traceback until
the environment is consistent — it is not an independent health check.

### 3.3 Version consistency check (do this after installing)

`uv pip list` / `pip list` must show both packages at the same version as `VERSION`,
and both editable installs must point at your working tree:

```bash
VIRTUAL_ENV="$OPEN_GATE_ENV" uv pip list | grep -i opengate
# opengate        <VERSION>   $OPEN_GATE_REPO
# opengate-core   <VERSION>   $OPEN_GATE_REPO/core
```

(`pip list` with the environment activated is equivalent.) A mismatch — e.g.
`opengate` at one version next to a tree at another — means one editable install is stale.
Editable installs are `.pth` files pointing at the source, so the *Python* code is always
current — but a **previously compiled `.so` is not**: the C++ extension keeps its old
bindings until you rebuild, and `opengate` then fails at import on a missing
`opengate_core.Gate*Actor`. See §4.6.

## 4. Full path — build Geant4, ITK and `opengate_core`

You need: a C++17 compiler, CMake, ~30 GB of disk, and patience (parallel `make -j N`).
Optional: Qt6 (install it **before** Geant4 if you want `opengate_visu`).

**Ask the user for `$OPEN_GATE_DEPS` first** (§0) — a non-volatile prefix, never `/tmp`.
Geant4 and ITK are each multi-GB builds that must survive reboots. Use subdirectories
named exactly `geant4.11-build` and `itk-build` inside it, because the commands below and
the resulting `CMAKE_PREFIX_PATH` assume that layout (CI caches the same shape under
`~/software`, see `.github/workflows/actions_build/action.yml`).

Before building anything, check whether usable builds already exist there and **reuse
them** — it saves 30+ minutes:

```bash
find "$OPEN_GATE_DEPS" -maxdepth 2 -name 'Geant4Config.cmake' 2>/dev/null
find "$OPEN_GATE_DEPS" -maxdepth 2 -name 'ITKConfig.cmake' 2>/dev/null
```

### 4.1 Geant4 `v11.4.2`

```bash
mkdir -p "$OPEN_GATE_DEPS"
cd "$OPEN_GATE_DEPS"
git clone --branch v11.4.2 https://github.com/Geant4/geant4.git --depth 1
mkdir geant4.11-build && cd geant4.11-build
cmake -DCMAKE_CXX_FLAGS=-std=c++17 \
      -DGEANT4_INSTALL_DATA=ON \
      -DGEANT4_INSTALL_DATADIR="$OPEN_GATE_DEPS/geant4/data" \
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
cd "$OPEN_GATE_DEPS"
git clone --branch v5.2.1 https://github.com/InsightSoftwareConsortium/ITK.git --depth 1
mkdir itk-build && cd itk-build
cmake -DCMAKE_CXX_FLAGS=-std=c++17 -DBUILD_TESTING=OFF ../ITK
make -j $(nproc)
```

Note: the CI pins ITK `v5.4.4` (`env.ITK_VERSION` in `main.yml`); the developer guide
still shows `v5.2.1`. Either works locally — use the CI version if you need to match CI.

### 4.3 `opengate_core` (C++ bindings)

```bash
cd "$OPEN_GATE_REPO/core"
export CMAKE_PREFIX_PATH="$OPEN_GATE_DEPS/geant4.11-build/:$OPEN_GATE_DEPS/itk-build/:${CMAKE_PREFIX_PATH}"
source "$OPEN_GATE_ENV/bin/activate"
python -m pip install -v -e .        # uv env: VIRTUAL_ENV="$OPEN_GATE_ENV" uv pip install -v -e .
```

On Windows use `;` as the `CMAKE_PREFIX_PATH` separator, not `:`.

This runs CMake and compiles the module in place; the build tree lands in `core/build/`.

### 4.4 `opengate` (Python)

```bash
cd "$OPEN_GATE_REPO"
source "$OPEN_GATE_ENV/bin/activate"
python -m pip install -v -e .        # uv env: VIRTUAL_ENV="$OPEN_GATE_ENV" uv pip install -e .
```

Because `opengate_core` is already installed from source, pip will not pull the wheel.
If pip *does* try to install `opengate-core==$(cat VERSION)` from PyPI, your editable
`opengate_core` is not visible in this environment — fix that instead of letting pip
overwrite it.

### 4.5 TLS workaround (only if §4.1 was built without `global-dynamic`)

```bash
export LD_PRELOAD="$OPEN_GATE_DEPS/geant4.11-build/lib/libG4processes.so:$OPEN_GATE_DEPS/geant4.11-build/lib/libG4geometry.so:${LD_PRELOAD}"
```

(Adjust the `lib/` sub-path to wherever Geant4 put its libraries; find them with
`find "$OPEN_GATE_DEPS/geant4.11-build" -name 'libG4processes.so'`.)

### 4.6 Rebuild when the C++ extension is stale (verified failure mode)

An editable `opengate_core` install picks up *Python* source changes immediately, but the
compiled extension `core/opengate_core.cpython-<ver>-<platform>.so` is only
rebuilt when you re-run the install. Pulling C++ changes without rebuilding therefore
produces an import-time failure on a binding that *does* exist in the sources.

Observed in a local dev environment (branch `agentic-skills`), before rebuilding:

```
AttributeError: module 'opengate_core' has no attribute 'GateDigitizerDeadTimeActor'.
Did you mean: 'GateDigitizerReadoutActor'?
```

raised from `opengate/actors/digitizers.py` (`class DigitizerDeadTimeActor(...)`), plus a
`RuntimeWarning: GATE PhysicsListBuilder registry differs from the linked Geant4` listing
physics lists as "missing C++ bindings". Both are symptoms of the same stale binary:
`GateDigitizerDeadTimeActor` exists in `core/opengate_core/opengate_lib/digitizer/` and is
registered in `core/opengate_core.cpp`. After rebuilding, both disappeared
and the suite went green.

Diagnose by comparing the `.so` timestamp with the sources — an `.so` older than the
`.cpp` files it wraps is stale:

```bash
ls -la "$OPEN_GATE_REPO"/core/opengate_core/*.so
cd "$OPEN_GATE_REPO" && git log -1 --format=%cd   # compare with the source tree's last change
```

`opengate_tests` does **not** catch this: `check_environment()`
(`opengate/bin/opengate_tests_helpers.py`) only warns about the Geant4 version and checks
the data folder, never the freshness of `opengate_core`.

Fix (from `core/`), then re-run the smoke test:

```bash
cd "$OPEN_GATE_REPO/core"
export CMAKE_PREFIX_PATH="$OPEN_GATE_DEPS/geant4.11-build/:$OPEN_GATE_DEPS/itk-build/:${CMAKE_PREFIX_PATH}"
source "$OPEN_GATE_ENV/bin/activate"
python -m pip install -v -e .        # uv env: VIRTUAL_ENV="$OPEN_GATE_ENV" uv pip install -v -e .
```

The compile is long (several minutes, single-threaded by default). Launch it detached
rather than in a foreground command that may time out, and follow the log — write the log
to a **non-volatile** file too, so it survives the session:

```bash
cd "$OPEN_GATE_REPO/core"
setsid sh -c "source '$OPEN_GATE_ENV/bin/activate' && python -m pip install -v -e . > \"$OPEN_GATE_ENV/core_rebuild.log\" 2>&1" \
  < /dev/null > /dev/null 2>&1 &
tail -f "$OPEN_GATE_ENV/core_rebuild.log"        # watch for '[100%]' and the final exit code
```

An existing `core/build/cmake.*/CMakeCache.txt` is reused, so `CMAKE_PREFIX_PATH` can be
omitted if the cache already points at Geant4/ITK builds (check with
`grep -E 'Geant4_DIR|ITK_DIR' "$OPEN_GATE_REPO"/core/build/*/CMakeCache.txt`).

After the rebuild, also refresh `opengate` itself so the two versions match `VERSION`
(§3.3), then confirm:

```bash
source "$OPEN_GATE_ENV/bin/activate"
cd "$OPEN_GATE_REPO"
opengate_tests -t actors/test008_dose_actor.py     # expect: 1/1 passed, 'True'
```

## 5. Optional extras some tests need

Several tests fail at import time without these; that is expected and not a regression.
Installing them is optional and requires the user's agreement (torch is a large download).

```bash
source "$OPEN_GATE_ENV/bin/activate"     # uv env: use `uv pip install` with VIRTUAL_ENV
python -m pip install torch             # CPU wheel is enough
# Linux CPU-only, lighter:
# python -m pip install torch --extra-index-url https://download.pytorch.org/whl/cpu
python -m pip install gaga_phsp         # >=0.7.6 in CI ('gaga-phsp' also resolves)
python -m pip install garf
python -m pip install pytomography hist
```

Not every test needs them: in this tree 11 of 458 test files are skipped just for missing
`torch` (reported as `--> Torch not avail`, `is_torch_available()` in
`opengate/bin/opengate_tests_helpers.py`). Check what the environment already has before
installing anything.

Additionally CI installs `SimpleITK` explicitly and, on Linux/Windows, extends the
library path using the helper script:

```bash
path=$(opengate_library_path.py -p site_packages)
export LD_LIBRARY_PATH="${path}/opengate_core.libs":${LD_LIBRARY_PATH}   # Linux
# Windows (git-bash): export PATH="${path}\\opengate_core.libs":${PATH}
```

## 6. Reproducing CI locally

CI (`.github/workflows/main.yml`) builds wheels on `ubuntu-24.04`, `macos-15`,
`windows-2025` for Python 3.10–3.14, then *installs the built wheels* and runs
`opengate_tests -r -s <sha>` (random subset + last 10 tests) inside
`.github/workflows/actions_tests/action.yml`.

To mimic it (note: this replaces your editable installs with wheels — do it in a scratch
environment, not the one you develop in):

```bash
source "$OPEN_GATE_ENV/bin/activate"        # required, see §3.1
cd "$OPEN_GATE_REPO"
python -m build                             # -> dist/
pip install dist/opengate_core-*.whl dist/opengate-*.whl
export GIT_SSL_NO_VERIFY=1
opengate_tests -r -s localsha
```

Remember the CI deletes `opengate/tests/data` before building the `opengate` wheel and
replaces it with a gitlink (`cp .git/modules/gam-tests/data/HEAD opengate/tests/`).

## 7. Verification checklist (do this before reporting anything)

```bash
cd "$OPEN_GATE_REPO"
cat user_secrets.json                     # must exist, real values, no CHANGE_ME
git check-ignore -v user_secrets.json     # must be ignored
source "$OPEN_GATE_ENV/bin/activate"      # MUST activate — see §3.1
python -c "import opengate, opengate_core; print(opengate.__file__); print(opengate_core.__file__)"
python -m pip list | grep -i opengate     # versions == VERSION  (uv env: uv pip list)
opengate_tests -t actors/test008_dose_actor.py      # one fast, representative test
```

- [ ] `user_secrets.json` exists, holds the **user's real** paths (no `CHANGE_ME`), and is
      **not** tracked by git (`git check-ignore -v user_secrets.json`).
- [ ] `OPEN_GATE_REPO` / `OPEN_GATE_ENV` were loaded from it, and the environment is
      **activated** (`which python` points into `$OPEN_GATE_ENV`).
- [ ] `$OPEN_GATE_ENV` is on **non-volatile** storage (`df -h "$OPEN_GATE_ENV"` shows a
      real filesystem, not `tmpfs`).
- [ ] `opengate.__file__` points into `$OPEN_GATE_REPO`.
- [ ] `opengate_core.__file__` matches the install you intended (source build vs wheel).
- [ ] Both packages report the same version as `VERSION` (§3.3); if not, refresh the
      install — a version-skewed editable `opengate_core` is the stale-`.so` case (§4.6).
- [ ] `ls "$OPEN_GATE_REPO/opengate/tests/data"` is non-empty.
- [ ] One targeted test passes (expect `1/1 … 'True'`).
- [ ] `pip list` / `uv pip list` recorded in your report if you are filing a bug.

A real, fully passing run looks like this (30-test slice, ~2.2 min):

```
Summary pass: 30/30 passed the tests:
Evaluation took in total:     2.2 min
True
```

## 8. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `No module named pip` / no `bin/pip` | `uv`-created venv: use `uv pip` (§3.1). |
| Every test fails with `ModuleNotFoundError: No module named 'opengate'`, including the auto-probe `misc/test001_g4threevector.py` | Venv not activated. The runner shells out to the literal command `python <test>` (§3.1). |
| `AttributeError: module 'opengate_core' has no attribute 'Gate...Actor'` | Stale compiled extension — rebuild `opengate_core` (§4.6). |
| `RuntimeWarning: … registry differs from the linked Geant4` | Same stale binary as above (§4.6) unless you genuinely edited the physics registry. |
| `Exception: Explicit test paths must point inside the OpenGATE tests/src folder` | `-t` path is wrong; it is relative to `opengate/tests/src` **with** the subdir (`actors/…`) (§3.2). |
| Silence for minutes, then Geant4 downloads | Expected on first `import opengate_core` (§3.2). |
| `ModuleNotFoundError: opengate_core` | You are in the wrong venv, or the C++ build failed. Re-run the install in `core/` (§4.3) and read the CMake output. |
| CMake cannot find Geant4/ITK | `CMAKE_PREFIX_PATH` unset, not built yet, or wrong separator (`:` on Linux/macOS, `;` on Windows). |
| `cannot allocate memory in static TLS block` | See §4.5, or rebuild Geant4 with `GEANT4_BUILD_TLS_MODEL=global-dynamic`. |
| Tests fail en masse with missing files | `opengate/tests/data` submodule not initialized (§2). |
| Download of Geant4/test data fails | `export GIT_SSL_NO_VERIFY=1` and retry. |
| Random test failures / crashes under load | CI runs many processes; reduce with `opengate_tests -n 4`. |
| Stale `*.so` after pulling C++ changes | Rebuild (§4.6); delete `core/build/` if inconsistent. |
| Builds or downloads vanish after a reboot | The environment or deps live on volatile storage — move them to a non-volatile path the user provides (§0). |

## 9. Clean-up / from-scratch reset

Only ever remove paths the user agreed to remove; `$OPEN_GATE_ENV` and `$OPEN_GATE_DEPS`
may be shared with other projects.

```bash
deactivate
df -h "$OPEN_GATE_ENV"                     # confirm which filesystem you are about to delete from
# rm -rf "$OPEN_GATE_ENV"                 # ask the user first
rm -rf "$OPEN_GATE_REPO/core/build" "$OPEN_GATE_REPO/core/CMakeFiles" "$OPEN_GATE_REPO/core/CMakeCache.txt"
cd "$OPEN_GATE_REPO" && git submodule update --init --recursive
rm -rf "$OPEN_GATE_REPO"/opengate/tests/output* "$OPEN_GATE_REPO"/opengate/tests/log
```

Never commit any of the removed paths — see `.gitignore`.
# Skill: environment-setup

**Goal:** obtain a virtual development environment in which the *whole* OpenGATE test
suite can run, prove it works before you change anything — and know how the project is
**built, packaged, released and tested in CI**.

Do not skip the verification step. A tree that imports `opengate` but runs against a
stale compiled `opengate_core` produces "wrong but plausible" failures that waste hours.

| Part | Sections | Use it when |
| --- | --- | --- |
| **Your environment** | §0–§5, §7–§9 | you need a machine where the suite runs |
| **Build, packaging & CI** | §6 | you release a version, touch wheels/packaging metadata, or edit `.github/workflows/` |

(The former `build-and-ci` skill is merged into §6 — there is no separate page to read.)

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
   compiled `opengate_core` newer than the C++ sources (§3.4, §4.6).

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
every install command below has two forms. **Watch out**: the very first command that
references an install (`python -m pip ...`) will fail with `No module named pip` and exit
non-zero if you picked the wrong form — check the exit status, do not assume a silent
`&&`-chained script succeeded.

**Never put build logs or build outputs under `/tmp`** (volatile): write long-running
build logs next to the environment or another user-provided non-volatile path.

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

### 2.1 Check the submodule is at the *recorded* commit, not just populated

A populated submodule can still be **behind** the commit this repo pins, in which case
reference data for some tests is missing and those tests fail with misleading comparison
errors while the test-data folder looks fine. This produced the only two failures in the
reference full-suite baseline (B-008/B-009). Compare the two hashes:

```bash
cd "$OPEN_GATE_REPO"
echo "expected: $(git ls-tree HEAD opengate/tests/data | awk '{print $3}')"
echo "actual  : $(git -C opengate/tests/data rev-parse HEAD)"
```

If they differ, fix it:

```bash
git submodule update --init --recursive opengate/tests/data
```

`git status` will **not** warn you: `git` does not track empty directories, and
`utility.create_output_ref()` creates the reference folder with `exist_ok=True`, so a missing
dataset leaves an empty directory behind rather than a clear error.

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

### 3.3 Check the **Geant4** version too (an environment property, not a repo bug)

Appendix: A wrong Geant4 version is an **environment problem** — the repository is fine;
fix the environment. Before trusting any result, confirm the linked Geant4 matches the
project's pin (`GEANT4_VERSION` in `.github/workflows/main.yml`, currently `v11.4.2`):

```bash
opengate_tests -l 2>&1 | head -5     # prints Detected / Required Geant4 version
```

Read it carefully — the runner only **warns**:

```
Detected Geant4 version: geant4-11-04 [MT]
Required Geant4 version: v11.4.2
11 4 2
11 4 0
Geant4 version is not ok. This means the environment is not completely up to date
```

Note Geant4's own encoding: **`geant4-11-04` means 11.4.0**; patch 2 is spelled
`geant4-11-04-patch-02` (`G4VERSION_NUMBER 1142`). So a bare `geant4-11-04` is *not* the
required 11.4.2 — it is the older 11.4.0. If you see `Geant4 version is not ok`, the
environment is **not** equivalent to CI: tests may fail for environment reasons, and any
physics-sensitive comparison is unreliable. **Fix the environment** (do not change the repo):
update the Geant4 checkout to the pinned tag, rebuild it, then relink `opengate_core`
(§4.1, §4.3, §4.6) before drawing conclusions from a failing suite.

Diagnose which Geant4 you actually have:

```bash
cd <geant4-source>              # the checkout CMAKE_HOME_DIRECTORY points at
git describe --tags            # e.g. 'v11.4.0' when the pin is v11.4.2
grep '#define G4VERSION_NUMBER' source/global/management/include/G4Version.hh
# 1140 -> 11.4.0 ; 1142 -> 11.4.2
```

This was a live finding on the current development environment (B-004 in
`skills/status/found-bugs.md`, classified there as an environment issue): the linked
Geant4 was 11.4.0 (`G4VERSION_NUMBER 1140`, `Geant4ConfigVersion.cmake` →
`set(PACKAGE_VERSION "11.4.0")`, checkout at tag `v11.4.0`) while CI pins 11.4.2.
The fix is `git fetch origin tag v11.4.2 && git checkout v11.4.2`, rebuild Geant4, then
relink `opengate_core`.

The check itself is also defective (B-005, a genuine repo bug): `get_required_g4_version()`
reads a CI job name that does not exist and silently falls back to a hard-coded `v11.4.2`,
so the "Required" line is not really coming from `main.yml`. Compare against `main.yml`
yourself.

### 3.4 Package version consistency check

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

The build is driven by `core/setup.py` (setuptools + a custom `CMakeBuild`), **not** by
scikit-build-core. Two things are worth knowing before you run it:

1. **How Geant4/ITK are located.** `setup.py` reads `core/config.json` (git-ignored,
   `.gitignore:61`) and passes `-DGeant4_DIR=<G4INSTALL>` / `-DITK_DIR=<ITKDIR>`. The file is
   absent by default, in which case it passes those as **empty** values and CMake falls back
   to discovering Geant4/ITK through `CMAKE_PREFIX_PATH` — which is why the command below sets
   it. The explicit, recommended way is to create the file:

   ```json
   { "G4INSTALL": "$OPEN_GATE_DEPS/geant4.11-build", "ITKDIR": "$OPEN_GATE_DEPS/itk-build" }
   ```

   (real absolute paths, no `$VARS`). The `G4INSTALL` / `ITKDIR` *environment* variables are
   also read, but **only as the defaults** — a present `config.json` overrides them.
2. **Parallelism comes from `os.cpu_count()`.** `setup.py` passes `-j<cpu_count>` to
   `cmake --build`, overridable with `OPEN_GATE_BUILD_JOBS=<n>` (e.g. to leave cores free).
   Until B-007 was fixed this was hardcoded to `-j4`; if you are on an older commit, expect
   only 4 jobs and add the override or build directly (below).

```bash
cd "$OPEN_GATE_REPO/core"
export CMAKE_PREFIX_PATH="$OPEN_GATE_DEPS/geant4.11-build/:$OPEN_GATE_DEPS/itk-build/:${CMAKE_PREFIX_PATH}"
source "$OPEN_GATE_ENV/bin/activate"
python -m pip install -v -e .        # uv env: VIRTUAL_ENV="$OPEN_GATE_ENV" uv pip install -v -e .
```

On Windows use `;` as the `CMAKE_PREFIX_PATH` separator, not `:`.

The command creates (or reuses) `core/build/cmake.<platform>-<impl>-<pyver>/` and compiles
the module in place. It **reuses the same directory across runs**, so most of the build is
already incremental — but note `setup.py` always re-runs `cmake` first, which re-configures
against whatever `Geant4_DIR`/`ITK_DIR` resolve to.

#### Make repeat builds faster (ccache / ninja / ccmake)

A cold compile is many minutes. Three supported speed-ups (all three tools were available on
the reference machine — verify on yours first):

```bash
which ccache ccmake ninja
```

**Configuring/building the existing tree directly** is the most reliable speed-up: the cache
survives between runs, so only changed translation units rebuild, and you control parallelism.
This is also how to relink quickly after swapping Geant4/ITK (§4.6):

```bash
cd "$OPEN_GATE_REPO/core/build/cmake.linux-x86_64-cpython-3.14"   # adjust to your platform tag
cmake -DGeant4_DIR="$OPEN_GATE_DEPS/geant4.11-build" \
      -DITK_DIR="$OPEN_GATE_DEPS/itk-build" .          # pick up the new deps
make -j $(nproc)                                          # incremental, all cores
```

**ccache** avoids recompiling identical translation units even after a clean build, and
compliments the above. It must be enabled *before* configuring — a build with no compiler
launcher ignores it entirely:

```bash
cd "$OPEN_GATE_REPO/core/build/cmake.linux-x86_64-cpython-3.14"
cmake -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache .
make -j $(nproc)
ccache -s          # hit rate should climb on subsequent builds
```

Verify whether ccache is actually wired in — an empty launcher means **no**, even when
`ccache` is installed:

```bash
grep -E 'CMAKE_CXX_COMPILER_LAUNCHER|CMAKE_CXX_COMPILER:' "$OPEN_GATE_REPO"/core/build/cmake.*/CMakeCache.txt
# CMAKE_CXX_COMPILER:STRING=/usr/bin/c++      <- no launcher: ccache unused
```

To make the launcher stick for the pip-driven build too, configure it once in the build
directory (as above) and then re-run the pip install: the cached launcher is honoured when
CMake reuses that directory.

**Ninja** (`-G Ninja`) builds faster than Make and computes staleness more precisely, but it
changes the recorded generator: only use it on a **fresh** build directory
(`rm -rf "$OPEN_GATE_REPO"/core/build`) and expect one full compile.

**ccmake** is a terminal UI for inspecting/editing the cache — handy to confirm
`Geant4_DIR`/`ITK_DIR` after a change:

```bash
ccmake "$OPEN_GATE_REPO/core/build/cmake.linux-x86_64-cpython-3.14"   # c=configure g=generate t=advanced
```

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

Fix (from `core/`), then re-run the smoke test. Use the **incremental** path (§4.3): the
build tree already exists, so re-configuring and re-running `make` rebuilds only what changed
— far faster than a fresh `pip install`, and it uses all cores instead of the pinned `-j4`:

```bash
cd "$OPEN_GATE_REPO/core/build/cmake.linux-x86_64-cpython-3.14"   # adjust platform tag
cmake -DGeant4_DIR="$OPEN_GATE_DEPS/geant4.11-build" \
      -DITK_DIR="$OPEN_GATE_DEPS/itk-build" .
make -j $(nproc)
```

If the cache is missing or you also want the editable install refreshed, fall back to the
full command:

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
(§3.4), then confirm:

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

## 6. Build, packaging and CI

This section is the single owner of the *build/release/CI* knowledge. If you only need a
working environment, stop here — §0–§5 are enough.

The repository ships **two** packages that must move together:

| Package | Source | Contents |
| --- | --- | --- |
| `opengate` | `opengate/`, `pyproject.toml`, `setup.py` | pure Python |
| `opengate_core` | `core/`, `core/setup.py` | C++ (pybind11) binding Geant4 + ITK, **shipped as a compiled wheel** |

`opengate` has a **hard pin** on its partner: `setup.py:15` sets
`install_requires=["opengate-core==" + version]`, where `version` is read from `VERSION`
(`core/setup.py:30` reads the same file). Consequence: **a version bump means republishing
both packages**, and any mismatch installs the wrong C++ layer.

### 6.1 CI topology — read `.github/workflows/main.yml`

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
| `test_wheel_pr` | installs the **built wheels** and runs the suite (see §6.3). |
| `publish_test` | publishes the results dashboard (master only). |

Triggers: push/PR to `master` (PRs are cancelled in progress if superseded), a
**scheduled** run (`cron '0 0 * * 0,3'`, i.e. Sun/Wed), and `workflow_dispatch`.
**`docs/**` is in `paths-ignore`** — a docs-only change does not run CI.

Helper files you may need to touch, all under `.github/workflows/`:
`actions_build/` (composite build action + `ci_build_wheel_{ubuntu,macos,windows}.sh`),
`actions_tests/action.yml`, the `Dockerfile_opengate_core*` images,
`createWheelLinux*.sh`, `delocateWindows.py`, `redoQt5LibsMac.py`.

### 6.2 Releasing a version — the three steps

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

### 6.3 What CI actually does when it tests

This is the part most often got wrong locally, because CI does **not** test an editable
install — it tests the **wheels**:

- `actions_tests/action.yml` deletes the workspace, downloads the artifacts, and installs
  `dist/opengate_core-*.whl` then `dist/opengate-*.whl`. A bug that only exists in the wheel
  (missing file in `MANIFEST`, a stray import) therefore appears **only in CI**.
- Matrix: `{ubuntu-24.04, macos-15, windows-2025} × Python 3.10–3.14`, excluding macOS and
  Windows on 3.10.
- Optional extras are installed explicitly: `torch`, `SimpleITK`, `gaga_phsp>=0.7.6`,
  `pytomography`, `hist`. A test that needs them passes in CI and is skipped locally (§5).
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

### 6.4 Reproducing CI locally

CI installs wheels into a scratch environment; do the same rather than testing your editable
install — a wheel-only bug cannot reproduce otherwise.

```bash
cd "$OPEN_GATE_REPO" && source "$OPEN_GATE_ENV/bin/activate"   # activation is required (§3.1)
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
- Full-suite parity means installing the optional extras of §5.
- A CI-only failure is usually one of: a file missing from the wheel, an extra only CI has,
  the `output_dashboard` path, or the platform's library path.

### 6.5 Packaging consequences of touching `core/`

The authoritative **build** procedure is §4.3 (Geant4/ITK, `core/config.json`, incremental
rebuild). Only the packaging/CI consequences belong here:

- Geant4/ITK are located via `core/config.json` (`G4INSTALL`, `ITKDIR`; git-ignored) or
  through `CMAKE_PREFIX_PATH` when the file is absent. The environment also reads the
  `G4INSTALL`/`ITKDIR` variables, but `config.json` **wins** when present.
- Parallelism is `os.cpu_count()`, overridable with `OPEN_GATE_BUILD_JOBS`
  (B-007 fixed the old hard-coded `-j4`).
- **An editable install never rebuilds the `.so`** — the failure is a misleading
  `AttributeError: module 'opengate_core' has no attribute 'Gate…'` (§4.6). Rebuild before
  concluding anything about a C++ change.
- A new binding must be registered in `core/opengate_core/opengate_core.cpp` **and** the
  extension rebuilt, or it does not exist at runtime.

### 6.6 Editing the workflows safely

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
  publication only happens on tags (§6.2).
- Local runs cannot reproduce the docker-based Linux build
  (`Dockerfile_opengate_core{,_arm64,_novis}`) — treat a Linux-wheel-specific failure as
  needing a CI run, not a local guess.
- Keep `paths-ignore: docs/**` in mind: a docs-only PR does not exercise the build.

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
- [ ] The **Geant4** version matches the CI pin (`opengate_tests -l | head -5`) — a
      mismatch is only a warning, and it invalidates comparison with CI (§3.3, B-004).
- [ ] Both packages report the same version as `VERSION` (§3.4); if not, refresh the
      install — a version-skewed editable `opengate_core` is the stale-`.so` case (§4.6).
- [ ] `ls "$OPEN_GATE_REPO/opengate/tests/data"` is non-empty, **and** the submodule HEAD
      matches `git ls-tree HEAD opengate/tests/data` (§2.1) — otherwise reference-data tests
      fail confusingly.
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
| `No module named pip` / no `bin/pip` | `uv`-created venv: use `uv pip` (§3.1). Also the cause of a sweepingly red build log that contains no compiler error — always check the exit code. |
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
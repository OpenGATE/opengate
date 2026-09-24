# Skill: `environment-setup/geant4-itk`

**Goal:** prepare the native dependencies `opengate_core` links against — **Geant4** and **ITK** —
and build the C++ extension itself.

This is the deep-dive companion to [`SKILL.md`](SKILL.md). Read `SKILL.md` first for the parts that
are *not* here: obtaining the virtual environment (§0–§3), the fast Python-only path, the optional
extras (§5), troubleshooting (§8) and the clean-up procedure (§9). Come here only when you actually
have to compile Geant4/ITK or rebuild `opengate_core` — the fast path in `SKILL.md` §3 does not
need any of this.

Related: [`build-and-ci.md`](build-and-ci.md) owns the *packaging and CI* consequences of the
build (§5 there); this file owns the *compilation*.

---

## 1. What you need, and what you must ask the user

You need: a C++17 compiler, CMake, ~30 GB of disk, and patience (parallel `make -j N`).
Optional: Qt6 (install it **before** Geant4 if you want `opengate_visu`).

**Ask the user for `$OPEN_GATE_DEPS` first** (`SKILL.md` §0) — a non-volatile prefix, never `/tmp`.
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

## 2. Geant4 `v11.4.2`

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

The version is pinned by the workflow (`env.GEANT4_VERSION` in
`.github/workflows/main.yml`); the runner warns when the linked Geant4 differs
(`SKILL.md` §3.3). Do not guess the pin — read it.

## 3. ITK

```bash
cd "$OPEN_GATE_DEPS"
git clone --branch v5.2.1 https://github.com/InsightSoftwareConsortium/ITK.git --depth 1
mkdir itk-build && cd itk-build
cmake -DCMAKE_CXX_FLAGS=-std=c++17 -DBUILD_TESTING=OFF ../ITK
make -j $(nproc)
```

Note: the CI pins ITK `v5.4.4` (`env.ITK_VERSION` in `main.yml`); the developer guide
still shows `v5.2.1`. Either works locally — use the CI version if you need to match CI.

## 4. `opengate_core` (C++ bindings)

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

### Make repeat builds faster (ccache / ninja / ccmake)

A cold compile is many minutes. Three supported speed-ups (all three tools were available on
the reference machine — verify on yours first):

```bash
which ccache ccmake ninja
```

**Configuring/building the existing tree directly** is the most reliable speed-up: the cache
survives between runs, so only changed translation units rebuild, and you control parallelism.
This is also how to relink quickly after swapping Geant4/ITK (§6):

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

## 5. `opengate` (Python)

```bash
cd "$OPEN_GATE_REPO"
source "$OPEN_GATE_ENV/bin/activate"
python -m pip install -v -e .        # uv env: VIRTUAL_ENV="$OPEN_GATE_ENV" uv pip install -e .
```

Because `opengate_core` is already installed from source, pip will not pull the wheel.
If pip *does* try to install `opengate-core==$(cat VERSION)` from PyPI, your editable
`opengate_core` is not visible in this environment — fix that instead of letting pip
overwrite it.

## 6. TLS workaround (only if §2 was built without `global-dynamic`)

```bash
export LD_PRELOAD="$OPEN_GATE_DEPS/geant4.11-build/lib/libG4processes.so:$OPEN_GATE_DEPS/geant4.11-build/lib/libG4geometry.so:${LD_PRELOAD}"
```

(Adjust the `lib/` sub-path to wherever Geant4 put its libraries; find them with
`find "$OPEN_GATE_DEPS/geant4.11-build" -name 'libG4processes.so'`.)

## 7. Rebuild when the C++ extension is stale (verified failure mode)

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

Fix (from `core/`), then re-run the smoke test. Use the **incremental** path (§4): the
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
(`SKILL.md` §3.4), then confirm:

```bash
source "$OPEN_GATE_ENV/bin/activate"
cd "$OPEN_GATE_REPO"
opengate_tests -t actors/test008_dose_actor.py     # expect: 1/1 passed, 'True'
```

## 8. Definition of done

- [ ] `$OPEN_GATE_DEPS` came from the user (`user_secrets.json`), is on non-volatile storage,
      and existing Geant4/ITK builds were checked for reuse first.
- [ ] Geant4 is built at the version pinned in the workflow, with `global-dynamic` TLS (or the
      §6 workaround is applied and recorded).
- [ ] ITK is built and its version is stated (CI pin vs. developer-guide version).
- [ ] `core/config.json` (or `CMAKE_PREFIX_PATH`) points at the right Geant4/ITK — the location
      that actually wins is the one you verified.
- [ ] After any C++ change, the extension was **rebuilt** (§7) — no conclusion drawn from a stale
      `.so`.
- [ ] `opengate_tests -t actors/test008_dose_actor.py` prints `Geant4 version is OK` and ends
      `1/1` / `True`.
- [ ] `opengate` and `opengate_core` both match `VERSION` (`SKILL.md` §3.4).

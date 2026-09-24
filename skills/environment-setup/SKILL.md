# Skill: environment-setup

**Goal:** obtain a virtual development environment in which the *whole* OpenGATE test
suite can run, prove it works before you change anything — and know how the project is
**built, packaged, released and tested in CI**.

Do not skip the verification step. A tree that imports `opengate` but runs against a
stale compiled `opengate_core` produces "wrong but plausible" failures that waste hours.

| Part | Sections | Use it when |
| --- | --- | --- |
| **Your environment** | §0–§3, §5, §7–§9 | you need a machine where the suite runs |
| **Build & CI deep-dives** | [`geant4-itk.md`](geant4-itk.md), [`build-and-ci.md`](build-and-ci.md) | you build Geant4/ITK/`opengate_core`, release a version, or debug a CI-only failure |

This file is the **index** for the environment work: §0–§3 and §5 get you a working environment,
§7–§9 verify and tidy it. The two things that need real depth live in their own files — read them
only when the task calls for it:

- **[`geant4-itk.md`](geant4-itk.md)** — compiling Geant4 and ITK and rebuilding the
  `opengate_core` C++ extension (§4 below is a pointer to it).
- **[`build-and-ci.md`](build-and-ci.md)** — packaging, releasing, and how CI tests the wheels
  (§6 below is a pointer to it).

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
| `OPEN_GATE_DEPS` | Where Geant4 and ITK are built or installed, in `<prefix>/geant4.11-build` and `<prefix>/itk-build` subdirectories. | Only needed for the full C++ path ([`geant4-itk.md`](geant4-itk.md)). Also non-volatile: these are ~10 GB builds. |

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
   compiled `opengate_core` newer than the C++ sources (§3.4, [`geant4-itk.md`](geant4-itk.md) §7).

If it passes all three, set `OPEN_GATE_ENV` to it and skip to §5/§7. If it fails, tell the
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
| Touching `core/**` (C++, bindings, Geant4/ITK behavior) | **Full path** ([`geant4-itk.md`](geant4-itk.md)): build Geant4, ITK and `opengate_core`. |
| Reproducing CI exactly / Qt visualization / debugging native crashes | **Full path** ([`geant4-itk.md`](geant4-itk.md)) + the CI-matching notes ([`build-and-ci.md`](build-and-ci.md) §5). |

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
(§3.3, [`geant4-itk.md`](geant4-itk.md) §2–§4, §7) before drawing conclusions from a failing suite.

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
`opengate_core.Gate*Actor`. See [`geant4-itk.md`](geant4-itk.md) §7.

## 4. Full path — build Geant4, ITK and `opengate_core`

**This section moved to its own file: [`geant4-itk.md`](geant4-itk.md).**

Read it only when you actually have to compile the native dependencies or rebuild the C++
extension. The fast path above (§3) does not need any of it. Where each piece now lives:

| You need to… | Where |
| --- | --- |
| Clone/build **Geant4** at the pinned version | [`geant4-itk.md`](geant4-itk.md) §2 |
| Build **ITK** | [`geant4-itk.md`](geant4-itk.md) §3 |
| Build **`opengate_core`** (bindings; `core/config.json`, parallelism, ccache/ninja) | [`geant4-itk.md`](geant4-itk.md) §4 |
| Install **`opengate`** against the source `opengate_core` | [`geant4-itk.md`](geant4-itk.md) §5 |
| Fix `cannot allocate memory in static TLS block` | [`geant4-itk.md`](geant4-itk.md) §6 |
| Fix a **stale `.so`** (`AttributeError: … has no attribute 'Gate…'`) | [`geant4-itk.md`](geant4-itk.md) §7 |

The two facts you need most often, stated here so you do not have to open it:

- **`$OPEN_GATE_DEPS` comes from the user** (§0) and must be on **non-volatile** storage —
  Geant4 and ITK are multi-GB builds that must survive reboots.
- **An editable install never rebuilds the `.so`.** Any C++ change needs a rebuild before you
  draw a conclusion; the symptom is a misleading `AttributeError` for a binding that *does*
  exist in the sources ([`geant4-itk.md`](geant4-itk.md) §7).

## 5. Optional extras — install ALL of them, then verify

Several tests fail at import time without these; that is expected and not a regression.
Installing them is optional and requires the user's agreement (torch is a large download).

> **Read this before installing.** The failure mode of this section is **installing only the
> package you happened to think of**. `torch` is the one people remember because it is the
> biggest, but the suite also needs `gaga_phsp`, `garf`, `pytomography`, `hist`, `pyvista` and
> `pymedphys`. Installing a subset leaves you with tests that are still skipped or still fail,
> and it is easy to misread that as a code problem. **Install the whole set, then run the audit
> in §5.1 to prove the environment is complete.**

### 5.0 The authoritative list — take it from CI, not from memory

`.github/workflows/actions_tests/action.yml` is what actually runs the suite in CI. Read it and
install exactly what it installs:

```bash
cd "$OPEN_GATE_REPO" && grep -nE "pip install" .github/workflows/actions_tests/action.yml
```

At the time of writing that is (plus `SimpleITK`, and `torch` — see §5.2 for how to choose its
version, which is platform-dependent):

```bash
source "$OPEN_GATE_ENV/bin/activate"     # uv env: use `uv pip install` with VIRTUAL_ENV
uv pip install --upgrade torch
uv pip install "gaga_phsp>=0.7.6"        # 'gaga-phsp' also resolves
uv pip install garf                      # needed by the garf/actor tests
uv pip install pytomography hist         # needed by external/pytomography/*
uv pip install pyvista                   # needed by the pyvista-based tests
uv pip install pymedphys                 # needed by the contrib 'test075...' tests
uv pip install SimpleITK
```

Any install may legitimately pull its own transitive dependencies (e.g. `pytomography` brings
`kornia`, `fft-conv-pytorch`, `torchrbf`) — that is expected, not a surprise.

### 5.1 Verify the environment is actually complete (do this every time)

Do **not** decide by eye which packages are needed. Ask the test tree what it imports and check
each one is importable — this catches the package you did not think of:

```bash
cd "$OPEN_GATE_REPO" && source "$OPEN_GATE_ENV/bin/activate"
python - <<'PY'
import ast, sys, pathlib, collections, importlib.util
src = pathlib.Path("opengate/tests/src")
local = {"opengate", "opengate_core", "utility", "gate", "tests"} | {p.stem for p in src.rglob("*.py")}
third = collections.defaultdict(set)
for f in src.rglob("*.py"):
    try:
        tree = ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        continue
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                third[a.name.split(".")[0]].add(f.name)
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            third[n.module.split(".")[0]].add(f.name)
missing = [(m, sorted(fs)) for m, fs in sorted(third.items())
           if m not in local and m not in sys.stdlib_module_names
           and importlib.util.find_spec(m) is None]
print("NOTHING MISSING" if not missing else "")
for m, fs in missing:
    print(f"MISSING {m}: {fs}")
PY
```

Expected output on a complete environment: **`NOTHING MISSING`**. Known false positives, safe to
ignore — these are **local modules of the test tree**, not PyPI packages (confirm with
`grep -rn "module <name>\|import <name>" opengate/tests/src | head`):

| Reported as missing | What it really is |
| --- | --- |
| `actors` | a **directory** under `opengate/tests/src/` imported by one visu test |
| `test043_garf_helpers` | a sibling helper module imported by the `test043_garf_*_wip.py` files |
| `coresi` | `opengate/contrib/compton_camera/coresi_helpers.py`, a local module |

Everything else in that list is a real gap — install it (§5.0). Do not proceed while a *real*
package is still missing: its tests will be skipped or fail, and you will be tempted to blame the
code.

Then confirm the *count*: the runner reports how many files it will execute, and installing the
extras should raise it. On the machine where this was written the count went **368 → 376** once
the extras were in place:

```bash
opengate_tests -t misc/test001_g4threevector.py | head -5    # look at the discovered-file count
```

A test that is still skipped prints its reason in the log (`--> Torch not avail`,
`--> pytomography not avail`): read it rather than assuming.

### 5.2 `torch` and `numpy` have a **per-platform** compatibility constraint — search, never copy a version list

**There is no portable “known good” set of `torch`/`numpy` versions for this project.** The
correct combination depends on the machine, so a version list copied from another session is a
bug waiting to happen. Determine it on the machine you are on.

**Why it is platform-specific.** `torch` is compiled against a specific NumPy C-ABI. A `torch`
wheel built against NumPy 1.x does **not** interoperate with NumPy ≥ 2: importing still succeeds
and plain tensors still work, but *any* bridge call fails, which is what breaks the GAN/`garf`
tests:

```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x …
RuntimeError: Numpy is not available      # on torch.from_numpy / .numpy() / DataLoader
```

Whether you can escape that by upgrading `torch` depends entirely on the platform, because
PyTorch publishes wheels per OS/architecture — and **drops them for architectures it no longer
builds**, e.g. there is **no Intel-macOS (`x86_64`) wheel newer than `torch 2.2.2`**, whereas Linux
and Apple Silicon have current releases on NumPy 2.

**The procedure — do this instead of copying versions:**

```bash
source "$OPEN_GATE_ENV/bin/activate"

# 1. What platform am I on, and is torch's numpy bridge actually broken?
python -c "import platform,sys;print(platform.platform(), platform.machine(), sys.version.split()[0])"
python -c "import torch,numpy as np;print(torch.__version__, np.__version__);\
print(torch.from_numpy(np.arange(3.0)).numpy())"      # fails => ABI mismatch

# 2. What is the NEWEST torch this platform can have? (dry-run changes nothing)
uv pip install --dry-run --upgrade torch

# 3. If a newer torch exists -> upgrade torch, keep numpy 2:
uv pip install --upgrade torch

# 4. If torch is already at its newest -> you must go DOWN to numpy 1.x.
#    Ask the resolver which numpy/partners are mutually consistent (no guesswork):
uv pip install --dry-run "numpy<2" torch
uv pip install --dry-run "numpy<2" torch pandas scipy      # partner downgrades it implies

# 5. Apply what the resolver agreed on, then RE-VERIFY the bridge (step 1).
```

Rules that follow:

- **Let the resolver decide the partners.** On Intel macOS the coherent set was
  `numpy 1.26.x` + `torch 2.2.2` **+ `pandas 2.x` + `scipy 1.12.x`** — `pandas 3` and `scipy ≥1.13`
  pull NumPy ≥ 2 back in, so asking only for `numpy<2 torch` silently fails or diverges. Always
  dry-run the *whole* set (step 4) and read what `uv` proposes.
- **Never leave a half-applied downgrade.** `uv` may abort the resolve and leave the environment
  untouched; check the exit status and the resulting `uv pip list`, then re-run step 1.
- **Re-verify the bridge after every change** — a successful install is not a working pair.
- **Record what you found, not what you hoped:** put the *platform* next to the versions, or the
  next agent will copy them onto a machine where they are wrong (this is the trap that produced
  B-012).
- If the downgrade is unacceptable for other work on that machine, use a **separate throwaway
  environment** for the torch tests rather than degrading the main one.

**Known-observed example (so you can recognise the pattern, *not* to copy the versions):** on
`macOS-15.8-x86_64` (Intel) with Python 3.12, the newest available `torch` was `2.2.2`, and the
coherent set was `numpy 1.26.4` + `pandas 2.3.3` + `scipy 1.12.0` + `torch 2.2.2`. On Apple
Silicon and Linux the same project takes a current `torch` with NumPy 2 and needs **no** downgrade.
The platform half of that sentence is the part that matters.

**Why CI does not catch this:** `.github/workflows/actions_tests/action.yml` installs torch on
`ubuntu-24.04` (`PLATFORM=x86_`), **`macos-15` (`PLATFORM=arm` — Apple Silicon)** and
`windows-2025`, i.e. only on platforms where PyTorch still ships current wheels. An Intel-Mac
developer therefore hits a failure CI structurally cannot reproduce — check the platform before
suspecting a `torch`-related test failure is a regression.

Additionally CI installs `SimpleITK` explicitly and, on Linux/Windows, extends the
library path using the helper script:

```bash
path=$(opengate_library_path.py -p site_packages)
export LD_LIBRARY_PATH="${path}/opengate_core.libs":${LD_LIBRARY_PATH}   # Linux
# Windows (git-bash): export PATH="${path}\\opengate_core.libs":${PATH}
```

## 6. Build, packaging and CI
**This section moved to its own file: [`build-and-ci.md`](build-and-ci.md).**

Read it when you **release a version**, touch wheels/packaging metadata, edit
`.github/workflows/`, or debug a **CI-only** failure. Where each piece now lives:

| You need to… | Where |
| --- | --- |
| Understand the two packages and the `opengate-core==<VERSION>` pin | [`build-and-ci.md`](build-and-ci.md) §1 |
| Read the CI job topology and the workflow-level pins | [`build-and-ci.md`](build-and-ci.md) §2 |
| **Release** a version (bump `VERSION`, republish both, tag) | [`build-and-ci.md`](build-and-ci.md) §3 |
| Know what CI actually tests (the **wheels**, not your editable install) | [`build-and-ci.md`](build-and-ci.md) §4 |
| **Reproduce CI locally** | [`build-and-ci.md`](build-and-ci.md) §5 |
| Know the packaging consequences of touching `core/` | [`build-and-ci.md`](build-and-ci.md) §6 |
| Edit the workflows safely (single source for each pin) | [`build-and-ci.md`](build-and-ci.md) §7 |

The fact that bites most often: **CI tests built wheels, not an editable install**, so a
wheel-only bug cannot reproduce locally unless you install the wheels too
([`build-and-ci.md`](build-and-ci.md) §5).

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
      install — a version-skewed editable `opengate_core` is the stale-`.so` case
      ([`geant4-itk.md`](geant4-itk.md) §7).
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
| `AttributeError: module 'opengate_core' has no attribute 'Gate...Actor'` | Stale compiled extension — rebuild `opengate_core` ([`geant4-itk.md`](geant4-itk.md) §7). |
| `RuntimeWarning: … registry differs from the linked Geant4` | Same stale binary as above ([`geant4-itk.md`](geant4-itk.md) §7) unless you genuinely edited the physics registry. |
| `Exception: Explicit test paths must point inside the OpenGATE tests/src folder` | `-t` path is wrong; it is relative to `opengate/tests/src` **with** the subdir (`actors/…`) (§3.2). |
| Silence for minutes, then Geant4 downloads | Expected on first `import opengate_core` (§3.2). |
| `ModuleNotFoundError: opengate_core` | You are in the wrong venv, or the C++ build failed. Re-run the install in `core/` ([`geant4-itk.md`](geant4-itk.md) §4) and read the CMake output. |
| CMake cannot find Geant4/ITK | `CMAKE_PREFIX_PATH` unset, not built yet, or wrong separator (`:` on Linux/macOS, `;` on Windows). |
| `cannot allocate memory in static TLS block` | See [`geant4-itk.md`](geant4-itk.md) §6, or rebuild Geant4 with `GEANT4_BUILD_TLS_MODEL=global-dynamic`. |
| Tests fail en masse with missing files | `opengate/tests/data` submodule not initialized (§2). |
| Download of Geant4/test data fails | `export GIT_SSL_NO_VERIFY=1` and retry. |
| Random test failures / crashes under load | CI runs many processes; reduce with `opengate_tests -n 4`. |
| Stale `*.so` after pulling C++ changes | Rebuild ([`geant4-itk.md`](geant4-itk.md) §7); delete `core/build/` if inconsistent. |
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
# MRCP OpenGATE 10.1 Compile And Build Guide

Date: 2026-05-19

This document records the exact compile/build process used for the OpenGATE 10.1 MRCP Tet mesh port.

## Source Tree

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate
```

## Build Directory

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build
```

## Required External Paths

Geant4:

```text
/Users/yhuh/Study/installation/geant/geant4114/build
```

Detected Geant4 version:

```text
11.4.0
```

ITK:

```text
/Users/yhuh/Study/installation/gate/Forgate10_tet/opengate/itk/ITK/build
```

Detected ITK version:

```text
5.2.1
```

Python:

```text
/opt/anaconda3/envs/tetGatev2/bin/python
```

Detected Python version:

```text
3.12.12
```

FFTW/Homebrew library paths:

```text
/opt/homebrew/opt/fftw/lib
/opt/homebrew/lib
```

## Important Dependency Note

The 10.1 worktree initially did not contain populated `core/external/pybind11` and `core/external/fmt` directories.

Configure failed with:

```text
core/external/pybind11 does not contain a CMakeLists.txt file
core/external/fmt does not contain a CMakeLists.txt file
Unknown CMake command "pybind11_add_module"
```

Fix used:

```bash
cp -R /Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate/core/external/pybind11/. \
  /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/external/pybind11/

cp -R /Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate/core/external/fmt/. \
  /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/external/fmt/
```

Because those folders were copied from git submodules, stale `.git` pointer files were removed:

```bash
rm core/external/fmt/.git core/external/pybind11/.git
```

## Configure Command

Run from:

```bash
cd /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build
```

Successful configure command:

```bash
/Applications/CMake-4.2.3.app/Contents/bin/cmake \
  -DGeant4_DIR="/Users/yhuh/Study/installation/geant/geant4114/build" \
  -DOPENGATE_USE_ITK=ON \
  -DITK_DIR="/Users/yhuh/Study/installation/gate/Forgate10_tet/opengate/itk/ITK/build" \
  -DPython_EXECUTABLE="/opt/anaconda3/envs/tetGatev2/bin/python" \
  -DPython3_EXECUTABLE="/opt/anaconda3/envs/tetGatev2/bin/python" \
  -DPython_ROOT_DIR="/opt/anaconda3/envs/tetGatev2" \
  -DPython3_ROOT_DIR="/opt/anaconda3/envs/tetGatev2" \
  -DPython_INCLUDE_DIR="/opt/anaconda3/envs/tetGatev2/include/python3.12" \
  -DPython_LIBRARY="/opt/anaconda3/envs/tetGatev2/lib/libpython3.12.dylib" \
  -DCMAKE_PREFIX_PATH="/opt/anaconda3/envs/tetGatev2;/opt/homebrew/opt/fftw;/opt/homebrew" \
  -DOPENGATE_USE_VISU=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SHARED_LINKER_FLAGS="-L/opt/homebrew/opt/fftw/lib" \
  ..
```

Why `Python_INCLUDE_DIR` and `Python_LIBRARY` are explicitly specified:

- CMake initially found the `tetGatev2` Python executable but failed to find `Development.Module`.
- Explicit include/library paths fixed this.

Successful configure output included:

```text
OPENGATE - Geant4 version 11.4.0
OPENGATE - Geant4 is compiled with MT (MultiThread)
OPENGATE - Geant4 is compiled with QT
Python_EXECUTABLE = /opt/anaconda3/envs/tetGatev2/bin/python
Python3_EXECUTABLE = /opt/anaconda3/envs/tetGatev2/bin/python
Found Python: /opt/anaconda3/envs/tetGatev2/bin/python
OPENGATE - ITK version = 5.2.1
Configuring done
Generating done
```

## Build Command

Run from:

```bash
cd /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build
```

Build command:

```bash
env LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /Applications/CMake-4.2.3.app/Contents/bin/cmake --build . --config Release -j4
```

Successful build result:

```text
[100%] Built target opengate_core
```

Warnings:

- macOS OpenGL deprecation warnings from `GateImageBox.cpp`.
- linker warning about duplicate `-lm`.

These warnings did not stop the build.

## Binding Verification

Run:

```bash
env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  -c "import opengate, opengate_core as g4; from opengate.actors.filters import filter_classes; print('opengate', opengate.__file__); print('core', g4.__file__); print('GateCopyNumberFilter', hasattr(g4, 'GateCopyNumberFilter'), 'CopyNumberFilter' in filter_classes); print('G4Tet', hasattr(g4, 'G4Tet')); print('build_tet_mesh_g4tet', hasattr(g4, 'build_tet_mesh_g4tet'))"
```

Expected output:

```text
GateCopyNumberFilter True True
G4Tet True
build_tet_mesh_g4tet True
```

Actual output:

```text
opengate /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/opengate/__init__.py
core /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build/opengate_core.cpython-312-darwin.so
GateCopyNumberFilter True True
G4Tet True
build_tet_mesh_g4tet True
```

## Build-Mode Geometry Check

Run:

```bash
cd /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build

env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  ./only_heart_ct_260320_v7_v14_20260429.py --mode build
```

Successful result:

```text
total tetrahedra=8582677
selected scoring tetrahedra=48012
engine initialize = 25.01 s
```

## Small Run Check

Before running, JSON was set to:

```json
"number_of_threads": 1,
"run_events": 5
```

Run:

```bash
cd /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build

env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  ./only_heart_ct_260320_v7_v14_20260429.py --mode run
```

Successful result:

```text
Simulation: START (around 5 events expected)
Simulation: STOP. Run: 1. Time: 136.9 seconds.
run = 139.90 s
total = 162.50 s
```

Output directory:

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build/output_v14_20260429_smalltest_10_1/dose_by_region
```

## Notes For Future Rebuild

If CMake accidentally picks `/opt/anaconda3/bin/python3.11` instead of `tetGatev2`, re-run configure with explicit:

```bash
-DPython_EXECUTABLE="/opt/anaconda3/envs/tetGatev2/bin/python"
-DPython_INCLUDE_DIR="/opt/anaconda3/envs/tetGatev2/include/python3.12"
-DPython_LIBRARY="/opt/anaconda3/envs/tetGatev2/lib/libpython3.12.dylib"
```

If `CopyNumberFilter` is missing after build, check:

- `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.cpp`
- `core/opengate_core/opengate_lib/filters/pyGateCopyNumberFilter.cpp`
- `core/opengate_core/opengate_core.cpp`
- `opengate/actors/filters.py`

If `build_tet_mesh_g4tet` is missing after build, check:

- `core/opengate_core/g4_bindings/GateTetMeshG4Tet.cpp`
- `core/opengate_core/opengate_core.cpp`

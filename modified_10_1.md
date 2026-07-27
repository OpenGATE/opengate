# Modified Files For MRCP Tet Mesh Port On OpenGATE 10.1.0

Date: 2026-05-19

Branch:

- `codex/mrcp-tet-10.1-port`

Base:

- OpenGATE `10.1.0`

Target tree:

- `/Users/yhuh/Study/installation/gate/Gate-10.1/opengate`

## Summary

The MRCP Tet mesh prototype previously developed on Gate-10.0.3 was ported to OpenGATE 10.1.0.

The most important 10.1-specific change is the filter API. In 10.1, C++ filters live under:

```text
core/opengate_core/opengate_lib/filters/
```

and custom filters should override:

```cpp
Evaluate(G4Step *step) const
```

instead of overriding `Accept(G4Step*)` directly. Therefore, `GateCopyNumberFilter` was adapted to the 10.1 filter design.

## Added Files

### Tet Mesh / G4Tet Binding

- `core/opengate_core/g4_bindings/GateTetMeshG4Tet.cpp`
  - Adds `build_tet_mesh_g4tet(...)`.
  - Reads TetGen `.node/.ele` files.
  - Builds the phantom using `G4PVParameterised`.
  - Provides copy-number based tetrahedron placement.
  - Supports region material/color/visibility maps.

- `core/opengate_core/g4_bindings/pyG4Tet.cpp`
  - Adds Python binding for `G4Tet`.
  - Adds `tet_is_degenerate(...)` helper.

### Copy Number Filter

- `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.h`
  - Declares the 10.1-compatible `GateCopyNumberFilter`.

- `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.cpp`
  - Implements `Evaluate(G4Step*) const`.
  - Accepts steps when the pre-step touchable copy number belongs to `copy_numbers`.

- `core/opengate_core/opengate_lib/filters/pyGateCopyNumberFilter.cpp`
  - Exposes `GateCopyNumberFilter` to Python via pybind11.

### Documentation

- `mrcp_10_1_port.md`
  - High-level porting summary.

- `compile_10_1.md`
  - Configure/build commands and verification commands.

- `modified_10_1.md`
  - This file.

## Modified Files

### `core/opengate_core/opengate_core.cpp`

Added init declarations and module registration calls for:

- `init_G4Tet`
- `init_GateTetMeshG4Tet`
- `init_GateCopyNumberFilter`

This makes the new C++ bindings visible from `opengate_core`.

### `core/opengate_core/g4_bindings/pyG4Material.cpp`

Added missing `G4Material::AddElement(...)` overload bindings used by custom MRCP material creation.

### `core/opengate_core/g4_bindings/pyG4VisAttributes.cpp`

Extended `G4VisAttributes` bindings:

- `SetColor`
- `SetVisibility`
- `SetForceSolid`
- `SetForceWireframe`

These are needed for region-specific visualization control.

### `opengate/actors/filters.py`

Added Python wrapper and registry entry for:

- `CopyNumberFilter`

This keeps the new 10.1 boolean/attribute filter system intact and only adds the MRCP-specific copy-number filter.

### `opengate/geometry/solids.py`

Added Tet helper utilities and `G4TetSolid` support used by the MRCP Tet mesh volume path.

### `opengate/geometry/volumes.py`

Added `G4TetVolume`, including:

- TetGen material parsing.
- MRCP region material/color/visibility mapping.
- Bounding box container construction.
- Call to `opengate_core.build_tet_mesh_g4tet(...)`.
- Proxy physical-volume registration for internally created Tet mesh PVs.

### `opengate/managers.py`

Registered new volume types:

- `G4TetVolume`
- `G4Tet`

Also added `proxy_volumes` lookup so internally created physical volumes can be referenced by actor/scoring logic.

## Example Files

The following v14 example files were copied into the 10.1 build directory:

- `core/build/only_heart_ct_260320_v7_v14_20260429.py`
- `core/build/only_heart_ct_helpers_v14_20260429.py`
- `core/build/only_heart_ct_config_v14_20260429.json`

MRCP input files were linked from the Gate-10.0.3 build directory instead of copied:

- `MRCP_AF.node`
- `MRCP_AF.ele`
- `MRCP_AF.material`
- `colour.dat`

## Verification Performed

### Python Syntax Check

Passed:

```bash
python -m py_compile \
  opengate/actors/filters.py \
  opengate/geometry/solids.py \
  opengate/geometry/volumes.py \
  opengate/managers.py \
  core/build/only_heart_ct_260320_v7_v14_20260429.py \
  core/build/only_heart_ct_helpers_v14_20260429.py
```

### CMake Configure

Passed with:

- Geant4 `11.4.0`
- Python `/opt/anaconda3/envs/tetGatev2/bin/python`
- Python version `3.12.12`
- ITK `5.2.1`

### C++ Build

Passed:

```bash
/Applications/CMake-4.2.3.app/Contents/bin/cmake --build . --config Release -j4
```

Result:

```text
[100%] Built target opengate_core
```

### Python Binding Check

Passed:

```text
GateCopyNumberFilter True True
G4Tet True
build_tet_mesh_g4tet True
```

### Example Build Mode Check

Command:

```bash
python ./only_heart_ct_260320_v7_v14_20260429.py --mode build
```

Result:

```text
tet mesh ready: total tetrahedra=8582677, selected scoring tetrahedra=48012
engine initialize = 25.01 s
```

The build-mode check completed successfully. It initialized full MRCP Tet geometry under OpenGATE 10.1.0.

No particle run or dose production was executed in this step.

## 2026-05-19 v15 Contrib-Style Refactor

Added a first cleanup layer toward the OpenGATE contrib phantom style.

New files:

- `opengate/contrib/phantoms/mrcp.py`
- `opengate/contrib/phantoms/mrcp_utils.py`
- `core/build/only_heart_ct_260320_v7_v15_20260519.py`
- `mrcp_10_1_v15_refactor_20260519.md`

Main changes:

- introduced `add_mrcp_phantom(...)` as a user-facing wrapper around the validated v14 MRCP Tet mesh setup;
- introduced `add_mrcp_dose_actors(...)` for CopyNumberFilter-based selected/per-organ dose scoring;
- introduced `MRCPPhantomInfo` and `MRCPDoseSettings` data classes;
- moved MRCP-specific reusable utility functions into `opengate/contrib/phantoms/mrcp_utils.py`;
- created a shorter v15 example that keeps only `--mode` as a command-line argument and reads execution settings from JSON;
- kept v14 source/world/physics/visualization reuse in the example intentionally, so v15 remains behavior-compatible with the validated v14 prototype.

Lightweight validation:

```bash
python -m py_compile \
  opengate/contrib/phantoms/mrcp.py \
  opengate/contrib/phantoms/mrcp_utils.py \
  core/build/only_heart_ct_260320_v7_v15_20260519.py
```

Result:

- passed;
- no full Geant4 run was started in this refactor step.

Additional v15 checks:

```bash
cd /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build

env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  ./only_heart_ct_260320_v7_v15_20260519.py --mode build
```

Result:

- full MRCP Tet geometry initialized successfully;
- total tetrahedra: `8582677`;
- selected scoring tetrahedra: `48012`;
- engine initialize time: `18.02 s`.

Small run check:

```bash
env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  ./only_heart_ct_260320_v7_v15_20260519.py --mode run
```

Result:

- JSON `run_events=5`, `threads=1`;
- `Simulation: START (around 5 events expected)`;
- 5 MRCP dose actors created;
- selected-region and per-region edep `.mhd/.raw` files generated.

VIS check:

```bash
env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  ./only_heart_ct_260320_v7_v15_20260519.py --mode vis
```

Result:

- visualization initialized;
- `Simulation: START (around 50 events expected)`;
- Qt window was confirmed by the user;
- run completed without segmentation fault.

After moving utility functions into `mrcp_utils.py`, build mode was run again and completed successfully:

- total tetrahedra: `8582677`;
- selected scoring tetrahedra: `48012`;
- engine initialize time: `17.62 s`.

Additional v15 independence cleanup:

- removed imports from `only_heart_ct_260320_v7_v14_20260429.py`;
- removed imports from `only_heart_ct_helpers_v14_20260429.py`;
- moved example-level world, physics, source, visualization, timing, and run-engine helper functions directly into `core/build/only_heart_ct_260320_v7_v15_20260519.py`;
- kept MRCP phantom/dose setup in `opengate.contrib.phantoms.mrcp`.

Validation after this cleanup:

- `python -m py_compile` passed for v15, `mrcp.py`, and `mrcp_utils.py`;
- `--mode build` completed successfully with `8582677` tetrahedra and `48012` selected scoring tetrahedra;
- `--mode run` with JSON `run_events=5` completed successfully;
- run time after cleanup: `130.76 s`;
- total time after cleanup: `152.55 s`.

v15 config/output naming cleanup:

- added `core/build/only_heart_ct_config_v15_20260519.json`;
- changed `core/build/only_heart_ct_260320_v7_v15_20260519.py` to read the v15 config by default;
- changed fallback output names in `opengate/contrib/phantoms/mrcp_utils.py` from v14-specific names to generic MRCP names;
- kept the config comments because the project loader strips full-line `//` and `#` comments before JSON parsing.

Validation:

- loader check confirmed `output_v15_20260519_smalltest_10_1`;
- loader check confirmed `output_g4tet_v15_20260519_smalltest_10_1`;
- `--mode build` completed using `only_heart_ct_config_v15_20260519.json`;
- v15 work directory was used for the generated hidden color file;
- engine initialize time: `17.46 s`.

Consolidated modified-file inventory:

- added `mrcp_10_1_all_modified_files_20260519.md`;
- this file lists all currently added/modified source, contrib, example, config, and documentation files;
- it also notes that `core/build` files are ignored by git but are still part of the tested local setup.

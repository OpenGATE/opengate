# MRCP Tet Mesh Port To OpenGATE 10.1.0

Date: 2026-05-19

This tree was created separately from the existing Gate-10.0.3 working tree:

- Source: `/Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate`
- Target: `/Users/yhuh/Study/installation/gate/Gate-10.1/opengate`
- Base tag: `10.1.0`

## What Was Ported

The MRCP/Tet mesh prototype from the Gate-10.0.3 tree was ported onto the OpenGATE `10.1.0` codebase.

Main additions:

- `core/opengate_core/g4_bindings/GateTetMeshG4Tet.cpp`
- `core/opengate_core/g4_bindings/pyG4Tet.cpp`
- `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.h`
- `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.cpp`
- `core/opengate_core/opengate_lib/filters/pyGateCopyNumberFilter.cpp`

Main modified files:

- `core/opengate_core/opengate_core.cpp`
- `core/opengate_core/g4_bindings/pyG4Material.cpp`
- `core/opengate_core/g4_bindings/pyG4VisAttributes.cpp`
- `opengate/actors/filters.py`
- `opengate/geometry/solids.py`
- `opengate/geometry/volumes.py`
- `opengate/managers.py`

Example files were copied into:

- `core/build/only_heart_ct_260320_v7_v14_20260429.py`
- `core/build/only_heart_ct_helpers_v14_20260429.py`
- `core/build/only_heart_ct_config_v14_20260429.json`

## Important 10.1 Change

OpenGATE 10.1 reorganized the C++ filter system:

- Filters now live under `core/opengate_core/opengate_lib/filters/`.
- `GateVFilter` uses `Evaluate(...)` as the virtual method.
- `Accept(...)` is handled by the base class and applies negation.

Therefore, `GateCopyNumberFilter` was adapted from the 10.0.3 implementation:

- 10.0.3 style: override `Accept(G4Step*)`
- 10.1 style: override `Evaluate(G4Step*) const`

This keeps the new 10.1 boolean/attribute filter system intact while adding MRCP organ scoring by Geant4 copy number.

## Current Verification

The 10.1 port was configured and built successfully on 2026-05-19.

Completed checks:

- `python -m py_compile` passed for the modified Python modules and v14 example/helper files.
- `git diff --check` passed.
- CMake configure passed with Geant4 `11.4.0`, ITK `5.2.1`, and Python `3.12.12` from `tetGatev2`.
- C++ build passed: `[100%] Built target opengate_core`.
- Python binding check passed:
  - `GateCopyNumberFilter`: available in `opengate_core` and registered in `opengate.actors.filters`.
  - `G4Tet`: available.
  - `build_tet_mesh_g4tet`: available.
- Example `--mode build` passed with full MRCP geometry:
  - total tetrahedra: `8582677`
  - selected scoring tetrahedra: `48012`
  - engine initialize: `25.01 s`

No particle run or dose production was executed in this step.

Next recommended checks:

1. Run a very small `--mode run` test after reducing `run_events` in the JSON.
2. Check output dose files for `heart` and `lung`.
3. Run `--mode vis` separately, preferably single-threaded, to confirm visualization behavior.

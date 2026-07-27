# MRCP OpenGATE 10.1 Modified Files

Date: 2026-05-19

This document lists the files modified or added for the MRCP Tet mesh OpenGATE 10.1.0 port.

## Repository Root

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate
```

## Branch

```text
codex/mrcp-tet-10.1-port
```

## Added Core C++ Files

### `core/opengate_core/g4_bindings/GateTetMeshG4Tet.cpp`

Purpose:

- Implements the main Tet mesh builder.
- Exposes `build_tet_mesh_g4tet(...)` to Python.
- Uses `G4PVParameterised`.
- Uses a custom nested parameterisation class to provide per-copy solid/material behavior.

Important locations:

- `GateTetNestedParam`: around the `class GateTetNestedParam` block.
- `ComputeMaterial(...)`: applies material/color/visibility per copy.
- `ComputeSolid(...)`: returns the `G4Tet` solid for each copy number.
- `build_tet_mesh_g4tet_internal(...)`: reads `.node/.ele`, creates solids, computes mesh center, creates dummy LV and `G4PVParameterised`.
- `init_GateTetMeshG4Tet(...)`: exports the function to Python.

Important design note:

- The code avoids mutating shared logical-volume material/visual attributes from Geant4 worker threads.
- This is important for MT stability.

### `core/opengate_core/g4_bindings/pyG4Tet.cpp`

Purpose:

- Exposes `G4Tet` to Python.
- Adds a simple degeneracy check helper.

Python-visible objects:

```python
opengate_core.G4Tet
opengate_core.tet_is_degenerate
```

### `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.h`

Purpose:

- Declares `GateCopyNumberFilter`.
- Uses the OpenGATE 10.1 filter API.

Key method:

```cpp
bool Evaluate(G4Step *step) const override;
```

### `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.cpp`

Purpose:

- Reads `copy_numbers` from Python user info.
- Accepts a step when the pre-step touchable copy number is in the configured set.

10.1-specific point:

- This file overrides `Evaluate(...)`, not `Accept(...)`.

### `core/opengate_core/opengate_lib/filters/pyGateCopyNumberFilter.cpp`

Purpose:

- Exposes `GateCopyNumberFilter` to Python through pybind11.

Python-visible object:

```python
opengate_core.GateCopyNumberFilter
```

## Modified Core C++ Files

### `core/opengate_core/opengate_core.cpp`

Purpose:

- Registers the new bindings.

Added declarations:

```cpp
void init_G4Tet(py::module &);
void init_GateCopyNumberFilter(py::module &);
void init_GateTetMeshG4Tet(py::module &);
```

Added initialization calls:

```cpp
init_G4Tet(m);
init_GateCopyNumberFilter(m);
init_GateTetMeshG4Tet(m);
```

### `core/opengate_core/g4_bindings/pyG4Material.cpp`

Purpose:

- Adds missing `G4Material::AddElement(...)` overload bindings.

Why needed:

- MRCP material construction reads element mass fractions from `.material`.
- Python code needs to create custom `G4Material` objects with those compositions.

Added bindings:

```cpp
AddElement(G4Element*, G4double)
AddElement(G4Element*, G4int)
```

### `core/opengate_core/g4_bindings/pyG4VisAttributes.cpp`

Purpose:

- Extends visualization attribute bindings.

Added/updated methods:

```cpp
SetColor(...)
SetVisibility(...)
SetForceSolid(...)
SetForceWireframe(...)
```

Why needed:

- region-specific colors,
- hidden organ visualization,
- solid/wireframe visualization controls.

## Modified Python Package Files

### `opengate/actors/filters.py`

Purpose:

- Adds Python-level `CopyNumberFilter`.
- Registers it in 10.1 `filter_classes`.

Added class:

```python
class CopyNumberFilter(FilterBase, g4.GateCopyNumberFilter)
```

Added registry entry:

```python
"CopyNumberFilter": CopyNumberFilter
```

Added processing:

```python
process_cls(CopyNumberFilter)
```

10.1-specific point:

- The existing 10.1 filter system was preserved.
- Only `CopyNumberFilter` was added.

### `opengate/geometry/solids.py`

Purpose:

- Adds helper functions for TetGen node bounds.
- Adds `G4TetSolid` support.

Important additions:

- `_read_node_bounds(...)`
- MRCP material/color parsing helper functions.
- `G4TetSolid`

### `opengate/geometry/volumes.py`

Purpose:

- Adds the main Python `G4TetVolume`.

Important additions:

- `PVProxyVolume`
- `G4TetVolume`
- `_build_region_dicts(...)`
- `construct(...)`
- `construct_solid(...)`
- `process_cls(G4TetVolume)`

What `G4TetVolume.construct(...)` does:

1. builds an outer container volume,
2. parses MRCP `.material`,
3. parses `colour.dat`,
4. creates region-specific `G4Material` objects,
5. calls `opengate_core.build_tet_mesh_g4tet(...)`,
6. registers internal physical volumes into `volume_manager.proxy_volumes`.

### `opengate/managers.py`

Purpose:

- Registers the new Tet volume type.
- Adds lookup support for internal proxy physical volumes.

Added import:

```python
G4TetVolume
```

Added volume types:

```python
"G4TetVolume": G4TetVolume
"G4Tet": G4TetVolume
```

Added storage:

```python
self.proxy_volumes = {}
```

Updated `get_volume(...)` behavior:

- checks regular volumes,
- checks parallel world volumes,
- then checks proxy volumes.

## Modified Example Files In Build Folder

These files are inside the build directory and may be ignored by git. They still matter for running the current example.

### `core/build/only_heart_ct_260320_v7_v14_20260429.py`

Purpose:

- Main user-facing example.
- Reads JSON config.
- Accepts `--mode build`, `--mode vis`, or `--mode run`.

Current usage:

```bash
python ./only_heart_ct_260320_v7_v14_20260429.py --mode run
```

### `core/build/only_heart_ct_helpers_v14_20260429.py`

Purpose:

- Helper functions for MRCP parsing, config parsing, dose actor creation, visualization preparation, and Tet phantom creation.

10.1-specific change:

OpenGATE 10.1 does not allow:

```python
sim.add_filter("CopyNumberFilter", "CF_name")
```

Therefore, the helper was changed to:

```python
from opengate.actors.filters import CopyNumberFilter

def make_copy_number_filter(name: str, copy_numbers: List[int]) -> CopyNumberFilter:
    filt = CopyNumberFilter(name=name)
    filt.copy_numbers = list(copy_numbers)
    return filt
```

and the dose actors now use:

```python
dose_actor.filter = make_copy_number_filter(...)
```

instead of:

```python
dose_actor.filters.append(...)
```

### `core/build/only_heart_ct_config_v14_20260429.json`

Purpose:

- Runtime configuration.

Current test values:

```json
"output_dir": "output_v14_20260429_smalltest_10_1",
"work_dir": "output_g4tet_v14_20260429_smalltest_10_1",
"number_of_threads": 1,
"run_events": 5
```

Backup before small-test modification:

```text
core/build/only_heart_ct_config_v14_20260429.json.bak_before_smalltest
```

## Added Documentation Files

```text
mrcp_10_1_port.md
compile_10_1.md
modified_10_1.md
mrcp_10_1_full_summary_20260519.md
mrcp_10_1_modified_files_20260519.md
mrcp_10_1_compile_build_20260519.md
mrcp_10_1_run_guide_20260519.md
```

## Files Not Stored In Git

The MRCP phantom data are not added to git.

In the 10.1 build folder they are symbolic links:

```text
MRCP_AF.node
MRCP_AF.ele
MRCP_AF.material
colour.dat
```

These point to the existing 10.0.3 build folder.

If another machine is used, those files must be placed in the 10.1 `core/build` directory or the JSON paths must be changed.

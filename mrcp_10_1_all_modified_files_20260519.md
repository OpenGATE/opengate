# MRCP Tet Mesh OpenGATE 10.1 Modified Files

Date: 2026-05-19

Workspace:

`/Users/yhuh/Study/installation/gate/Gate-10.1/opengate`

This document lists the files added or modified for the MRCP Tet mesh import/scoring work on OpenGATE 10.1.

## 1. Important Note About `core/build`

The directory `core/build/` is ignored by the repository `.gitignore`.

Therefore, files such as the v15 example and config do not appear in normal `git status`, even though they exist and were tested.

Ignored but intentionally created files:

- `core/build/only_heart_ct_260320_v7_v15_20260519.py`
- `core/build/only_heart_ct_config_v15_20260519.json`

Existing v14 build/example files also remain in `core/build`:

- `core/build/only_heart_ct_260320_v7_v14_20260429.py`
- `core/build/only_heart_ct_helpers_v14_20260429.py`
- `core/build/only_heart_ct_config_v14_20260429.json`

## 2. Core C++ / Pybind Files

### 2.1 `core/opengate_core/g4_bindings/GateTetMeshG4Tet.cpp`

Status:

- Added.

Purpose:

- Implements the core MRCP/TetGen tetrahedral mesh geometry builder.
- Reads `.node` and `.ele` TetGen files.
- Creates per-copy `G4Tet` solids.
- Uses `G4PVParameterised` with a `G4VNestedParameterisation`-style class instead of placing every tetrahedron manually.
- Supports copy-number semantics needed for organ/region scoring.

Main features:

- `build_tet_mesh_g4tet(...)`
- `build_tet_mesh_g4tet_compat(...)`
- `GateTetNestedParam::ComputeSolid(...)`
- `GateTetNestedParam::ComputeMaterial(...)`
- `GateTetNestedParam::ComputeTransformation(...)`

Important behavior:

- `copyNo` corresponds to the tetrahedron order after the `.ele` file is read.
- Region IDs are extracted from the `.ele` material/attribute field.
- Region-specific materials are returned from `ComputeMaterial(...)`.
- Region visibility/color information is handled in the parameterisation path.

Why this matters:

- This is the main geometry performance improvement.
- It moves the implementation closer to the original Geant4 MRCP phantom design, where many tetrahedra are handled through parameterisation rather than independent Python/OpenGATE placements.

### 2.2 `core/opengate_core/g4_bindings/pyG4Tet.cpp`

Status:

- Added.

Purpose:

- Adds Python binding for `G4Tet`.

Main changes:

- Exposes a `G4Tet` constructor.
- Exposes `GetCubicVolume(...)`.
- Exposes `Inside(...)`.
- Adds helper `tet_is_degenerate(...)` for simple tetrahedron degeneracy checks.

Why this matters:

- Allows OpenGATE Python/C++ integration to refer to Geant4 tetrahedral solids.
- Supports debugging and lower-level validation of Tet geometry.

### 2.3 `core/opengate_core/g4_bindings/pyG4Material.cpp`

Status:

- Modified.

Main changes:

- Added bindings for `G4Material::AddElement(...)`.
- Both overload styles are exposed:
  - by mass fraction;
  - by number of atoms.

Why this matters:

- MRCP `.material` files define tissue compositions from elemental mass fractions.
- Without `AddElement`, Python/C++ binding code cannot build custom tissue materials from those compositions.

### 2.4 `core/opengate_core/g4_bindings/pyG4VisAttributes.cpp`

Status:

- Modified.

Main changes:

- Expanded `G4VisAttributes` binding.
- Added/updated:
  - `SetColor(...)`
  - `SetVisibility(...)`
  - `SetForceSolid(...)`
  - `SetForceWireframe(...)`

Why this matters:

- MRCP region visualization needs per-region color and visibility handling.
- This was required while debugging skin/outer-shell hiding and organ-specific colors.

### 2.5 `core/opengate_core/opengate_core.cpp`

Status:

- Modified.

Main changes:

- Registered new pybind initializers:
  - `init_G4Tet(...)`
  - `init_GateCopyNumberFilter(...)`
  - `init_GateTetMeshG4Tet(...)`

Why this matters:

- Without registration here, the new C++ bindings are compiled but not exposed in `opengate_core`.

## 3. Copy Number Filter Files

### 3.1 `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.h`

Status:

- Added.

Purpose:

- Declares a new OpenGATE filter that accepts or rejects steps based on Geant4 touchable copy number.

Main field:

- `std::set<int> fCopyNumbers`

### 3.2 `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.cpp`

Status:

- Added.

Purpose:

- Implements the copy-number based filtering logic.

Main behavior:

- Reads `copy_numbers` from user info.
- During `Evaluate(G4Step*)`, gets the pre-step touchable copy number.
- Accepts the step only if the copy number is in the configured set.
- If `copy_numbers` is empty, the filter accepts all steps.

Why this matters:

- MRCP region scoring should be based on tetrahedron copy numbers, not only material names.
- This fixes the earlier semantic issue where organ dose could be confused with material-filtered dose.

### 3.3 `core/opengate_core/opengate_lib/filters/pyGateCopyNumberFilter.cpp`

Status:

- Added.

Purpose:

- Exposes `GateCopyNumberFilter` to Python through pybind11.

## 4. OpenGATE Python API Files

### 4.1 `opengate/actors/filters.py`

Status:

- Modified.

Main changes:

- Added Python class `CopyNumberFilter`.
- Registered it in `filter_classes`.
- Added `process_cls(CopyNumberFilter)`.

Why this matters:

- Allows Python code to create and attach:

```python
from opengate.actors.filters import CopyNumberFilter

f = CopyNumberFilter(name="CF_heart")
f.copy_numbers = [...]
actor.filter = f
```

OpenGATE 10.1 note:

- OpenGATE 10.1 deprecates older `sim.add_filter(...)` usage.
- The current implementation uses `actor.filter = CopyNumberFilter(...)`.

### 4.2 `opengate/geometry/solids.py`

Status:

- Modified.

Main changes:

- Added Tet/MRCP helper logic for:
  - reading `.node` bounds;
  - parsing material-related information;
  - supporting `G4Tet` solid metadata.

Why this matters:

- This supports the Python-side `G4Tet` volume definition and basic bounding/metadata handling.

Current cleanup note:

- Some helper code here is still prototype-like.
- For a final upstream Pull Request, some MRCP-specific parsing may be better located under `opengate/contrib/phantoms/mrcp_utils.py` instead of general geometry core files.

### 4.3 `opengate/geometry/volumes.py`

Status:

- Modified.

Main changes:

- Added `G4TetVolume`.
- Added MRCP `.material` parsing and material creation support.
- Added color/visibility parsing support from `colour.dat`.
- Added support for calling the C++ builder `oc.build_tet_mesh_g4tet(...)`.
- Added proxy-volume handling so actors can attach to the generated parameterised physical volume.

Main behavior:

- User can create a Tet phantom with:

```python
phantom = sim.add_volume("G4Tet", "phantom_tetmesh")
phantom.node_file = "MRCP_AF.node"
phantom.ele_file = "MRCP_AF.ele"
phantom.material_file = "MRCP_AF.material"
phantom.color_file = "colour.dat"
phantom.scale = 10.0
```

Why this matters:

- This is the main OpenGATE Python-level volume integration point for the MRCP Tet phantom.

Current cleanup note:

- Some comments/markers are still prototype-style.
- For a clean PR, comments should be normalized and MRCP-specific material parsing should be reviewed for placement.

### 4.4 `opengate/managers.py`

Status:

- Modified.

Main changes:

- Imported `G4TetVolume`.
- Registered volume types:
  - `"G4TetVolume"`
  - `"G4Tet"`
- Added `proxy_volumes` storage.
- Updated volume lookup so actors can resolve proxy volumes created by the parameterised Tet mesh builder.

Why this matters:

- Allows `sim.add_volume("G4Tet", ...)`.
- Allows dose actors to attach to the Tet phantom/proxy volume.

## 5. Contrib-Style MRCP Files

### 5.1 `opengate/contrib/phantoms/mrcp.py`

Status:

- Added.

Purpose:

- Introduces a first contrib-style public API for MRCP phantoms.

Main public API:

```python
from opengate.contrib.phantoms.mrcp import (
    add_mrcp_phantom,
    add_mrcp_dose_actors,
    MRCPDoseSettings,
)
```

Main objects/functions:

- `MRCPPhantomInfo`
- `MRCPDoseSettings`
- `add_mrcp_phantom(...)`
- `add_mrcp_dose_actors(...)`
- `load_mrcp_json_config(...)`

Main behavior:

- Adds MRCP Tet phantom using `simulation.add_volume("G4Tet", name)`.
- Reads TetGen file paths from user arguments.
- Builds region-to-copy-number maps.
- Supports full-phantom geometry with selected-organ scoring.
- Adds aggregate selected-region dose actor.
- Adds per-region dose actors when requested.
- Uses `CopyNumberFilter` directly with `actor.filter = ...`.

Why this matters:

- Moves the user-facing design toward the style suggested by OpenGATE collaborators:

```python
phantom = add_mrcp_phantom(sim, name="mrcp", phantom_type="adult_female", data_path="...")
add_mrcp_dose_actors(sim, phantom, ...)
```

### 5.2 `opengate/contrib/phantoms/mrcp_utils.py`

Status:

- Added.

Purpose:

- Holds MRCP-specific utility functions that should not live in the user example script.

Main contents:

- unit helper;
- JSON-with-comments loader;
- config application;
- `.node` bounds reader;
- `.ele` stream filter;
- region-to-copy-number map builder;
- selected copy-number flattening;
- `.material` region keyword selection;
- visualization color file helper;
- common DoseActor construction helper.

Why this matters:

- Removes the direct dependency of `mrcp.py` on the earlier v14 helper script.
- Makes the package structure closer to a future `opengate.contrib.phantoms.mrcp` PR.

## 6. Example / Config Files In `core/build`

These files are ignored by git but are part of the current working setup.

### 6.1 `core/build/only_heart_ct_260320_v7_v15_20260519.py`

Status:

- Added in `core/build`.
- Ignored by git because `core/build/` is ignored.

Purpose:

- Provides the current short user-facing MRCP test example.
- Uses `opengate.contrib.phantoms.mrcp`.
- Keeps only `--mode` as a command-line argument.
- Reads all other settings from JSON.

Main behavior:

```bash
python ./only_heart_ct_260320_v7_v15_20260519.py --mode build
python ./only_heart_ct_260320_v7_v15_20260519.py --mode run
python ./only_heart_ct_260320_v7_v15_20260519.py --mode vis
```

Recent cleanup:

- Removed imports from v14 example/helper files.
- Now contains its own example-level:
  - `configure_world(...)`
  - `configure_physics(...)`
  - `spectrum_generation(...)`
  - `configure_source(...)`
  - `setup_vis(...)`
  - `get_simulation_engine(...)`
  - `run_engine(...)`
  - `tnow(...)`

### 6.2 `core/build/only_heart_ct_config_v15_20260519.json`

Status:

- Added in `core/build`.
- Ignored by git because `core/build/` is ignored.

Purpose:

- v15-specific config file.

Important settings:

```text
output_dir = output_v15_20260519_smalltest_10_1
work_dir   = output_g4tet_v15_20260519_smalltest_10_1
scoring_keywords = ["heart", "lung"]
show_all_organs = true
per_region_dose = true
run_events = 5
build_vis_events = 50
number_of_threads = 1
```

Note:

- The file contains full-line `//` comments for readability.
- It is not strict JSON for `python -m json.tool`.
- It is valid for this project because `load_json_config(...)` strips full-line `//` and `#` comments before parsing.

## 7. Documentation Files

### 7.1 `compile_10_1.md`

Status:

- Added.

Purpose:

- Records OpenGATE 10.1 compile/configure information.

### 7.2 `modified_10_1.md`

Status:

- Added and repeatedly updated.

Purpose:

- Running summary of modified files and validation steps.

### 7.3 `mrcp_10_1_port.md`

Status:

- Added.

Purpose:

- Summary of the OpenGATE 10.1 port.

### 7.4 `mrcp_10_1_compile_build_20260519.md`

Status:

- Added.

Purpose:

- Detailed compile/build instructions for the 10.1 port.

### 7.5 `mrcp_10_1_full_summary_20260519.md`

Status:

- Added.

Purpose:

- Full project summary up to the 10.1 migration.

### 7.6 `mrcp_10_1_modified_files_20260519.md`

Status:

- Added.

Purpose:

- Earlier modified-files summary.

### 7.7 `mrcp_10_1_run_guide_20260519.md`

Status:

- Added.

Purpose:

- Runtime guide for setting up shell environment and running examples.

### 7.8 `mrcp_10_1_v15_refactor_20260519.md`

Status:

- Added and updated.

Purpose:

- Tracks the v15 refactor:
  - contrib-style API;
  - `mrcp_utils.py` split;
  - v15 config/output naming;
  - build/run/vis validation results.

### 7.9 `mrcp_10_1_all_modified_files_20260519.md`

Status:

- Added.

Purpose:

- This file.
- Consolidated list of all currently added/modified files and their roles.

## 8. Validation Summary

### 8.1 Binding Checks

Previously confirmed:

```text
GateCopyNumberFilter True True
G4Tet True
build_tet_mesh_g4tet True
```

### 8.2 v15 Syntax Check

Passed:

```bash
python -m py_compile \
  core/build/only_heart_ct_260320_v7_v15_20260519.py \
  opengate/contrib/phantoms/mrcp.py \
  opengate/contrib/phantoms/mrcp_utils.py
```

### 8.3 v15 Build Mode

Passed:

```text
Using config file: only_heart_ct_config_v15_20260519.json
MRCP phantom 'phantom_tetmesh' ready: total tetrahedra=8582677, selected scoring tetrahedra=48012
engine initialize = 17.46 s
```

### 8.4 v15 Run Mode

Passed with small test settings:

```text
run_events = 5
Created 5 MRCP dose actor(s)
Simulation: START (around 5 events expected)
Simulation: STOP
```

Generated dose outputs:

```text
selected_regions_edep.mhd/raw
Heart_wall_8700_edep.mhd/raw
Blood_in_heart_chamber_8800_edep.mhd/raw
Lung_AI__left_9700_edep.mhd/raw
Lung_AI__right_9900_edep.mhd/raw
```

### 8.5 v15 Visualization Mode

Passed:

```text
Simulation: initialize Visualization
Simulation: START (around 50 events expected)
Simulation: STOP
```

The Qt visualization window was confirmed visually by the user.

## 9. Current Git Status Summary

Tracked modified files:

```text
core/opengate_core/g4_bindings/pyG4Material.cpp
core/opengate_core/g4_bindings/pyG4VisAttributes.cpp
core/opengate_core/opengate_core.cpp
opengate/actors/filters.py
opengate/geometry/solids.py
opengate/geometry/volumes.py
opengate/managers.py
```

Untracked source/code files:

```text
core/opengate_core/g4_bindings/GateTetMeshG4Tet.cpp
core/opengate_core/g4_bindings/pyG4Tet.cpp
core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.cpp
core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.h
core/opengate_core/opengate_lib/filters/pyGateCopyNumberFilter.cpp
opengate/contrib/phantoms/mrcp.py
opengate/contrib/phantoms/mrcp_utils.py
```

Untracked documentation files:

```text
compile_10_1.md
modified_10_1.md
mrcp_10_1_compile_build_20260519.md
mrcp_10_1_full_summary_20260519.md
mrcp_10_1_modified_files_20260519.md
mrcp_10_1_port.md
mrcp_10_1_run_guide_20260519.md
mrcp_10_1_v15_refactor_20260519.md
mrcp_10_1_all_modified_files_20260519.md
```

Ignored but important build/example files:

```text
core/build/only_heart_ct_260320_v7_v15_20260519.py
core/build/only_heart_ct_config_v15_20260519.json
```

## 10. Remaining Cleanup Before Upstream PR

Recommended before opening an OpenGATE Pull Request:

- Move or redesign MRCP-specific material parsing currently placed in general geometry files.
- Remove prototype markers such as personal insert comments.
- Decide whether config should be `.jsonc` instead of `.json`.
- Add a minimal automated test that does not require redistributing MRCP data.
- Add documentation under the OpenGATE documentation structure.
- Decide external data handling with OpenGATE collaborators because MRCP data may be freely accessible but not necessarily redistributable through GitHub.
- Confirm whether `core/build` example files should be moved to a proper `examples` or `contrib` test location.

# MRCP Tet Mesh OpenGATE 10.1 Full Summary

Date: 2026-05-19

## Purpose

This document summarizes the current OpenGATE 10.1 port of the MRCP Tet mesh phantom work.

The goal was to move the existing Gate-10.0.3 MRCP Tet mesh implementation into a separate OpenGATE 10.1.0 tree and verify that:

- MRCP Tet mesh geometry can be imported.
- `G4PVParameterised` Tet geometry is available through `opengate_core`.
- organ/region dose scoring still works with `CopyNumberFilter`.
- the same small heart/lung dose outputs are generated as in the 10.0.3 version.
- visual mode opens successfully.

## Directory Layout

Original 10.0.3 working tree:

```text
/Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate
```

New 10.1 working tree:

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate
```

10.1 branch:

```text
codex/mrcp-tet-10.1-port
```

10.1 base version:

```text
OpenGATE 10.1.0
```

The 10.1 tree was created from the local git tag:

```bash
git worktree add /Users/yhuh/Study/installation/gate/Gate-10.1/opengate 10.1.0
git switch -c codex/mrcp-tet-10.1-port
```

## What Was Implemented

### 1. Tet Mesh Geometry Import

The 10.1 tree now includes a Tet mesh builder exposed through `opengate_core`.

Core function exposed to Python:

```python
opengate_core.build_tet_mesh_g4tet(...)
```

This builder:

- reads TetGen `.node` and `.ele` files,
- builds one `G4Tet` solid per tetrahedron,
- places the full mesh through `G4PVParameterised`,
- assigns region-specific materials,
- assigns region-specific colors and visibility,
- keeps the full phantom geometry by default.

### 2. G4Tet Python Binding

`G4Tet` is now exposed to Python:

```python
hasattr(opengate_core, "G4Tet") == True
```

The binding also includes a helper:

```python
opengate_core.tet_is_degenerate(...)
```

### 3. Copy Number Based Scoring

The 10.1 port uses a `CopyNumberFilter`.

Why this is needed:

- each tetrahedron placed by `G4PVParameterised` has a Geant4 copy number;
- `.ele` region IDs are mapped to lists of copy numbers;
- heart/lung scoring is performed by accepting only steps whose copy number belongs to the selected organ/region.

This is more semantically correct than filtering by material name.

### 4. 10.1 Filter API Adaptation

OpenGATE 10.1 changed the filter system.

In 10.0.3, the earlier custom filter used:

```cpp
Accept(G4Step *step)
```

In 10.1, the correct design is:

```cpp
Evaluate(G4Step *step) const
```

The 10.1 `GateVFilter::Accept(...)` method applies negation and calls `Evaluate(...)`.

Therefore, `GateCopyNumberFilter` was adapted to override `Evaluate(...)`.

### 5. Example Helper API Adaptation

OpenGATE 10.1 no longer allows:

```python
sim.add_filter("CopyNumberFilter", "filter_name")
```

It raises:

```text
add_filter is deprecated, use my_actor.filter = my_filter
```

The v14 helper in the 10.1 build folder was therefore updated to create filters directly:

```python
from opengate.actors.filters import CopyNumberFilter

filt = CopyNumberFilter(name="CF_selected_regions")
filt.copy_numbers = list(copy_numbers)
dose_actor.filter = filt
```

This was required for `--mode run` to work in OpenGATE 10.1.

## Current Example

Main example:

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build/only_heart_ct_260320_v7_v14_20260429.py
```

Helper:

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build/only_heart_ct_helpers_v14_20260429.py
```

Config:

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build/only_heart_ct_config_v14_20260429.json
```

Current test config values:

```json
"output_dir": "output_v14_20260429_smalltest_10_1",
"work_dir": "output_g4tet_v14_20260429_smalltest_10_1",
"number_of_threads": 1,
"run_events": 5
```

The previous JSON was backed up as:

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build/only_heart_ct_config_v14_20260429.json.bak_before_smalltest
```

## MRCP Input Data

The 10.1 build folder uses symbolic links to the existing 10.0.3 MRCP data files:

```text
MRCP_AF.node     -> /Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate/core/build/MRCP_AF.node
MRCP_AF.ele      -> /Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate/core/build/MRCP_AF.ele
MRCP_AF.material -> /Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate/core/build/MRCP_AF.material
colour.dat       -> /Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate/core/build/colour.dat
```

This avoids duplicating large phantom files.

## Verification Results

### Python Binding Check

The following bindings were confirmed:

```text
GateCopyNumberFilter True True
G4Tet True
build_tet_mesh_g4tet True
```

Meaning:

- `GateCopyNumberFilter` exists in `opengate_core`.
- `CopyNumberFilter` is registered in `opengate.actors.filters`.
- `G4Tet` exists.
- `build_tet_mesh_g4tet` exists.

### 10.1 Small Run

Command:

```bash
python ./only_heart_ct_260320_v7_v14_20260429.py --mode run
```

Settings:

```text
run_events = 5
number_of_threads = 1
scoring_keywords = ["heart", "lung"]
show_all_organs = true
```

Result:

```text
total tetrahedra = 8582677
selected scoring tetrahedra = 48012
setup/geometry = 4.88 s
engine initialize = 17.72 s
run = 139.90 s
total = 162.50 s
```

Generated files:

```text
output_v14_20260429_smalltest_10_1/dose_by_region/selected_regions_edep.mhd
output_v14_20260429_smalltest_10_1/dose_by_region/selected_regions_edep.raw
output_v14_20260429_smalltest_10_1/dose_by_region/Heart_wall_8700_edep.mhd
output_v14_20260429_smalltest_10_1/dose_by_region/Heart_wall_8700_edep.raw
output_v14_20260429_smalltest_10_1/dose_by_region/Blood_in_heart_chamber_8800_edep.mhd
output_v14_20260429_smalltest_10_1/dose_by_region/Blood_in_heart_chamber_8800_edep.raw
output_v14_20260429_smalltest_10_1/dose_by_region/Lung_AI__left_9700_edep.mhd
output_v14_20260429_smalltest_10_1/dose_by_region/Lung_AI__left_9700_edep.raw
output_v14_20260429_smalltest_10_1/dose_by_region/Lung_AI__right_9900_edep.mhd
output_v14_20260429_smalltest_10_1/dose_by_region/Lung_AI__right_9900_edep.raw
```

The generated `.raw` files were about `110 MB` each.

### 10.0.3 Comparison Run

Equivalent small test was run in:

```text
/Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate/core/build
```

Settings:

```text
run_events = 5
number_of_threads = 1
```

Result:

```text
total tetrahedra = 8582677
selected scoring tetrahedra = 48012
setup/geometry = 4.53 s
engine initialize = 17.47 s
run = 131.69 s
total = 153.69 s
```

Output file names matched the 10.1 run.

### Dose Image Metadata Comparison

The `selected_regions_edep.mhd` metadata matched between 10.1 and 10.0.3:

```text
NDims = 3
Offset = -252.5 -135 -815
ElementSpacing = 2.5 2.5 2.5
DimSize = 203 109 653
ElementType = MET_DOUBLE
ElementDataFile = selected_regions_edep.raw
```

### Visual Mode

Visual mode was launched in the 10.1 tree:

```bash
python ./only_heart_ct_260320_v7_v14_20260429.py --mode vis
```

The Qt visualization window was confirmed on screen by the user.

Note:

- automated screenshot capture was not used as final evidence because macOS captured the wrong active desktop/window during the attempt.
- for a reliable screenshot, manually bring the Qt window to the front and use macOS screenshot capture, or use `/vis/viewer/save` if the active Geant4 Qt viewer supports it in the current session.

## Current Status

The 10.1 port is functionally validated at the small-test level:

- CMake configure: passed.
- C++ build: passed.
- Python binding import: passed.
- small `--mode run`: passed.
- heart/lung output file generation: passed.
- 10.0.3 output structure comparison: passed.
- visual mode window: confirmed.

The next recommended step is to run a larger but still controlled test, for example:

```json
"run_events": 100,
"number_of_threads": 1
```

Then compare:

- run time,
- memory usage,
- output file metadata,
- nonzero dose/edep voxel counts.

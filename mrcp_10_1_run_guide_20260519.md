# MRCP OpenGATE 10.1 Run Guide

Date: 2026-05-19

This document explains how to run the MRCP Tet mesh example after opening a new terminal.

## 1. Open Terminal

Use a terminal where the `tetGatev2` conda environment is available.

Activate the environment:

```bash
conda activate tetGatev2
```

Check Python:

```bash
which python
python --version
```

Expected Python:

```text
/opt/anaconda3/envs/tetGatev2/bin/python
Python 3.12.12
```

## 2. Go To The 10.1 Build Directory

```bash
cd /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build
```

## 3. Set Runtime Environment

The safest way is to set `PYTHONPATH` and `DYLD_LIBRARY_PATH` in the same command.

Common prefix:

```bash
env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python
```

Why this matters:

- `PYTHONPATH` makes Python use the 10.1 local `opengate` package and the freshly built `opengate_core.cpython-312-darwin.so`.
- `DYLD_LIBRARY_PATH` helps find FFTW/Homebrew libraries at runtime.

## 4. Check The Build Is Being Used

Run:

```bash
env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  -c "import opengate, opengate_core as g4; from opengate.actors.filters import filter_classes; print(opengate.__file__); print(g4.__file__); print(hasattr(g4, 'GateCopyNumberFilter')); print('CopyNumberFilter' in filter_classes); print(hasattr(g4, 'build_tet_mesh_g4tet'))"
```

Expected:

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/opengate/__init__.py
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build/opengate_core.cpython-312-darwin.so
True
True
True
```

## 5. Check Input Files

The example expects these files in the build directory:

```text
MRCP_AF.node
MRCP_AF.ele
MRCP_AF.material
colour.dat
```

Current 10.1 setup uses symbolic links:

```bash
ls -l MRCP_AF.node MRCP_AF.ele MRCP_AF.material colour.dat
```

Current links point to:

```text
/Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate/core/build/
```

If running on another machine, either copy these files into `core/build` or edit the JSON file paths.

## 6. Edit JSON Settings

Config file:

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build/only_heart_ct_config_v14_20260429.json
```

Important fields:

```json
"scoring_keywords": ["heart", "lung"],
"show_all_organs": true,
"aggregate_selected_regions": true,
"per_region_dose": true,
"number_of_threads": 1,
"run_events": 5,
"dose_spacing_mm": 2.5
```

Current file is set for a small test:

```json
"output_dir": "output_v14_20260429_smalltest_10_1",
"work_dir": "output_g4tet_v14_20260429_smalltest_10_1",
"number_of_threads": 1,
"run_events": 5
```

Backup before the small-test edit:

```text
only_heart_ct_config_v14_20260429.json.bak_before_smalltest
```

## 7. Build-Only Geometry Check

This initializes geometry without doing a full particle run.

```bash
env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  ./only_heart_ct_260320_v7_v14_20260429.py --mode build
```

Expected key output:

```text
tet mesh ready: total tetrahedra=8582677, selected scoring tetrahedra=48012
Simulation: initialize Actors
```

## 8. Small Run Test

This was already tested successfully with `run_events=5`.

```bash
env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  ./only_heart_ct_260320_v7_v14_20260429.py --mode run
```

Expected output:

```text
Simulation: START (around 5 events expected)
Simulation: STOP
```

Expected output directory:

```text
output_v14_20260429_smalltest_10_1/dose_by_region
```

Expected dose files:

```text
selected_regions_edep.mhd
selected_regions_edep.raw
Heart_wall_8700_edep.mhd
Heart_wall_8700_edep.raw
Blood_in_heart_chamber_8800_edep.mhd
Blood_in_heart_chamber_8800_edep.raw
Lung_AI__left_9700_edep.mhd
Lung_AI__left_9700_edep.raw
Lung_AI__right_9900_edep.mhd
Lung_AI__right_9900_edep.raw
```

Check files:

```bash
find output_v14_20260429_smalltest_10_1/dose_by_region -maxdepth 1 -type f | sort
```

Check image metadata:

```bash
sed -n '1,40p' output_v14_20260429_smalltest_10_1/dose_by_region/selected_regions_edep.mhd
```

Expected metadata:

```text
NDims = 3
Offset = -252.5 -135 -815
ElementSpacing = 2.5 2.5 2.5
DimSize = 203 109 653
ElementType = MET_DOUBLE
```

## 9. Visual Mode

Run:

```bash
env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  ./only_heart_ct_260320_v7_v14_20260429.py --mode vis
```

Notes:

- VIS mode is forced to single-thread in the script for Qt/Geant4 stability.
- Qt window was confirmed to open on screen.
- If the window appears blank at first, use the Geant4 Qt session command area.

Useful Geant4 Qt commands:

```text
/vis/viewer/set/viewpointThetaPhi 90 0
/vis/viewer/zoom 1.2
/vis/viewer/flush
```

To show trajectories:

```text
/tracking/storeTrajectory 1
/vis/modeling/trajectories/create/drawByParticleID
/vis/scene/add/trajectories smooth
/run/beamOn 1
```

To manually save a screenshot:

- bring the Qt window to the front,
- use macOS screenshot shortcut,
- save the image near the build directory if needed.

Automated `screencapture` may capture the wrong active window if the Qt window is not frontmost.

## 10. Compare With 10.0.3

10.0.3 comparison directory:

```text
/Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate/core/build
```

10.0.3 small-test output:

```text
output_v14_20260429_smalltest_10_0_3/dose_by_region
```

10.1 small-test output:

```text
/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build/output_v14_20260429_smalltest_10_1/dose_by_region
```

Compare file names:

```bash
find /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build/output_v14_20260429_smalltest_10_1/dose_by_region -name '*.mhd' -exec basename {} \; | sort

find /Users/yhuh/Study/installation/gate/Gate-10.0.3/opengate/core/build/output_v14_20260429_smalltest_10_0_3/dose_by_region -name '*.mhd' -exec basename {} \; | sort
```

Both should show:

```text
Blood_in_heart_chamber_8800_edep.mhd
Heart_wall_8700_edep.mhd
Lung_AI__left_9700_edep.mhd
Lung_AI__right_9900_edep.mhd
selected_regions_edep.mhd
```

## 11. Known Caveats

Small `run_events` values still take a long time because:

- full Tet geometry has `8582677` tetrahedra,
- navigation/actor overhead is large,
- output image grids are full phantom grids,
- each `.raw` file is about `110 MB`.

For production tests, increase events carefully and monitor memory.

Recommended next test:

```json
"number_of_threads": 1,
"run_events": 100
```

Then later test multi-thread behavior only after single-thread results are stable.

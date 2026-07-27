# MRCP Tetrahedral Phantom Support

## Overview

This contribution adds support for loading Mesh-type Reference Computational
Phantoms (MRCPs) represented as TetGen tetrahedral meshes. It provides:

- an OpenGATE `TetrahedralMesh` volume type;
- TetGen `.node` and `.ele` mesh loading;
- region-specific materials and visualization attributes;
- adult female (`MRCP_AF`) and adult male (`MRCP_AM`) phantom helpers;
- copy-number filtering for region-specific scoring; and
- helper functions for creating aggregate and per-region dose actors.

This branch is based on OpenGATE 10.1.1. Compatibility with the current
upstream `master` branch must still be verified before opening an upstream
pull request.

## Public Python API

### Add an MRCP phantom

```python
from opengate.contrib.phantoms.mrcp import add_mrcp_phantom

phantom = add_mrcp_phantom(
    simulation,
    name="mrcp",
    phantom_type="MRCP_AF",
    data_path="/path/to/mrcp/data",
)
```

Supported `phantom_type` values are:

- `adult_female`, `MRCP_AF`, and `mrcp_af`;
- `adult_male`, `MRCP_AM`, and `mrcp_am`.

Selecting an adult male phantom changes the default input filenames to
`MRCP_AM.node`, `MRCP_AM.ele`, and `MRCP_AM.material`. Explicitly supplied
filenames are not replaced, so custom datasets can be used:

```python
phantom = add_mrcp_phantom(
    simulation,
    phantom_type="MRCP_AM",
    node_file="custom.node",
    ele_file="custom.ele",
    material_file="custom.material",
)
```

### Add a tetrahedral mesh directly

```python
mesh = simulation.add_volume("TetrahedralMesh", "mesh")
mesh.node_file = "/path/to/mesh.node"
mesh.ele_file = "/path/to/mesh.ele"
mesh.material_file = "/path/to/mesh.material"
mesh.color_file = "/path/to/colour.dat"
mesh.scale = 10.0
mesh.material = "G4_Galactic"
mesh.default_material = "G4_WATER"
```

`TetrahedralMeshVolume` constructs a bounding-box envelope and populates it
with parameterised `G4Tet` daughters. TetGen describes the input format;
`TetrahedralMesh` describes the OpenGATE volume type.

### Add MRCP dose actors

```python
from opengate.contrib.phantoms.mrcp import (
    MRCPDoseSettings,
    add_mrcp_dose_actors,
)

settings = MRCPDoseSettings(
    spacing_mm=2.5,
    aggregate_selected_regions=True,
    per_region=True,
)

actors = add_mrcp_dose_actors(
    simulation,
    phantom,
    units,
    settings,
)
```

The helper can create a combined scoring actor for selected regions, separate
actors for individual regions, and an optional unfiltered full-grid actor.

## Copy-number filtering

`CopyNumberFilter` selects Geant4 steps using the copy number at touchable
history depth zero:

```python
from opengate.actors.filters import CopyNumberFilter

copy_filter = CopyNumberFilter(name="selected_tetrahedra")
copy_filter.copy_numbers = [0, 1, 2]
```

An empty `copy_numbers` list accepts all copy numbers.

## Implementation structure

| Component | Location | Responsibility |
|---|---|---|
| `TetrahedralMeshEnvelopeSolid` | `opengate/geometry/solids.py` | Calculates the mesh bounds and creates the envelope solid. |
| `TetrahedralMeshVolume` | `opengate/geometry/volumes.py` | Creates the envelope and invokes the C++ tetrahedral-mesh builder. |
| `GateTetrahedralMeshParameterisation` | `core/opengate_core/opengate_lib/` | Supplies per-copy tetrahedral solids, materials, regions, and visualization attributes. |
| `pyGateTetrahedralMesh.cpp` | `core/opengate_core/opengate_lib/` | Exposes the tetrahedral-mesh builder to Python. |
| `GateCopyNumberFilter` | `core/opengate_core/opengate_lib/filters/` | Performs Geant4 copy-number filtering. |
| `mrcp.py` | `opengate/contrib/phantoms/` | Provides the public phantom and dose-actor helpers. |
| `mrcp_utils.py` | `opengate/contrib/phantoms/` | Parses MRCP material/color data and prepares region mappings. |

## Input data

The MRCP dataset is not included in this contribution. A dataset normally
contains:

- a TetGen `.node` file;
- a TetGen `.ele` file;
- an MRCP `.material` file; and
- an optional `colour.dat` file.

The `.ele` region attribute is used to assign materials and to build
copy-number groups for scoring.

## Build and validation

The changes include C++ and pybind11 sources, so the OpenGATE core must be
rebuilt before using the new Python API. Validation should cover:

1. a clean core build;
2. import of the rebuilt `opengate_core` module;
3. MRCP_AF and MRCP_AM geometry construction;
4. custom input filenames;
5. overlap checks and visualization;
6. copy-number-filtered energy-deposition scoring; and
7. single-thread and multi-thread execution where supported.

Build commands and dependency paths are environment-specific and are
intentionally not stored in this repository-level document.

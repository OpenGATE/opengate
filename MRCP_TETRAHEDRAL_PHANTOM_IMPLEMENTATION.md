# MRCP Tetrahedral Phantom Implementation

## Purpose

This document describes the source changes required to add MRCP tetrahedral
phantom support to OpenGATE. It complements
[`MRCP_TETRAHEDRAL_PHANTOM.md`](MRCP_TETRAHEDRAL_PHANTOM.md), which documents
the user-facing API.

The implementation introduces a parameterised Geant4 tetrahedral volume,
region-specific materials and visualization, copy-number filtering, and
contrib helpers for MRCP geometry and dose scoring.

## Change summary

| Area | Change | Main responsibility |
|---|---|---|
| Geant4 bindings | Extended | Expose the Geant4 APIs required to construct tetrahedra, materials, and visualization attributes. |
| OpenGATE C++ core | Added | Parse TetGen geometry and construct parameterised `G4Tet` copies. |
| Filtering | Added | Accept or reject steps according to Geant4 copy numbers. |
| Python geometry | Extended | Register and construct the `TetrahedralMesh` volume type. |
| MRCP contrib module | Added | Load MRCP_AF/MRCP_AM datasets and configure region-based scoring. |

Relative to the OpenGATE 10.1.1 tag, this implementation changes 15 source
files: 9 new files and 6 modified files. Documentation files are counted
separately.

## New source files

| File | Main symbol or component | Role |
|---|---|---|
| `core/opengate_core/g4_bindings/pyG4Tet.cpp` | `G4Tet` binding | Exposes the Geant4 tetrahedral solid constructor and related methods to Python. |
| `core/opengate_core/opengate_lib/GateTetrahedralMeshParameterisation.h` | `GateTetrahedralMeshParameterisation` | Declares the parameterisation and public TetGen mesh-builder functions. |
| `core/opengate_core/opengate_lib/GateTetrahedralMeshParameterisation.cpp` | `build_tetrahedral_mesh_from_tetgen()` | Parses TetGen nodes/elements and provides per-copy solids, materials, regions, and visualization attributes. |
| `core/opengate_core/opengate_lib/pyGateTetrahedralMesh.cpp` | `init_GateTetrahedralMesh()` | Registers the tetrahedral-mesh builders in `opengate_core`. |
| `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.h` | `GateCopyNumberFilter` | Declares a Geant4 step filter based on physical-volume copy numbers. |
| `core/opengate_core/opengate_lib/filters/GateCopyNumberFilter.cpp` | `GateCopyNumberFilter::Evaluate()` | Reads the pre-step touchable copy number and evaluates the configured selection. |
| `core/opengate_core/opengate_lib/filters/pyGateCopyNumberFilter.cpp` | `init_GateCopyNumberFilter()` | Exposes the C++ copy-number filter to Python. |
| `opengate/contrib/phantoms/mrcp.py` | `add_mrcp_phantom()` | Provides the public MRCP_AF/MRCP_AM phantom and dose-actor API. |
| `opengate/contrib/phantoms/mrcp_utils.py` | MRCP parsing helpers | Parses material and color files, creates materials, selects regions, and prepares scoring maps. |

The accompanying `MRCP_TETRAHEDRAL_PHANTOM.md` file describes the public API,
inputs, build requirements, and validation scope.

## Modified source files

| File | Modified area | Purpose |
|---|---|---|
| `core/opengate_core/g4_bindings/pyG4Material.cpp` | `G4Material::AddElement` overloads | Exposes element addition by mass fraction and by number of atoms for MRCP material construction. |
| `core/opengate_core/opengate_core.cpp` | Module declarations and initialization | Registers `GateCopyNumberFilter` and the tetrahedral-mesh builder in the Python module. |
| `opengate/actors/filters.py` | `CopyNumberFilter` and `filter_classes` | Adds the Python filter class, user configuration, and manager lookup registration. |
| `opengate/geometry/solids.py` | `TetrahedralMeshEnvelopeSolid` | Reads TetGen node bounds and constructs the enclosing box solid. |
| `opengate/geometry/volumes.py` | `TetrahedralMeshVolume` | Builds materials and visualization dictionaries, constructs the envelope, and invokes the C++ mesh builder. |
| `opengate/managers.py` | Volume class import and alias handling | Makes `simulation.add_volume("TetrahedralMesh", name)` resolve to `TetrahedralMeshVolume`. |

OpenGATE 10.1.1 already provides the `G4VisAttributes::SetForceSolid` and
`SetForceWireframe` bindings required by this feature. The earlier local
binding changes were therefore not carried into this branch.

## Geometry construction flow

1. `simulation.add_volume("TetrahedralMesh", name)` creates a
   `TetrahedralMeshVolume`.
2. `TetrahedralMeshEnvelopeSolid` reads the `.node` file and determines the
   scaled bounding box.
3. `TetrahedralMeshVolume` parses region materials and visualization settings.
4. `build_tetrahedral_mesh_from_tetgen()` reads the `.node` and `.ele` files.
5. `GateTetrahedralMeshParameterisation` supplies a `G4Tet`, material, region,
   and visualization attributes for each parameterised copy.
6. A `G4PVParameterised` daughter is placed inside the envelope logical
   volume.

The term `TetrahedralMesh` identifies the OpenGATE volume. The term `TetGen`
is retained only for the supported input-file format. `G4Tet` continues to
identify one Geant4 tetrahedral solid.

## MRCP material flow

1. `mrcp_utils.py` parses the MRCP material definitions and organ-to-material
   mapping.
2. Chemical elements and `G4Material` objects are created from the supplied
   density and elemental fractions.
3. Region identifiers from the `.ele` file are mapped to material pointers.
4. Missing or unselected regions fall back to `default_material`.
5. Optional color data are converted to per-region RGBA and visibility
   settings.

## Region scoring flow

1. The MRCP helper builds a region-to-copy-number map from the `.ele` file.
2. Requested organ names are resolved to region identifiers.
3. `CopyNumberFilter` receives the corresponding tetrahedron copy numbers.
4. Dose actors use the filter for aggregate or per-region scoring.

The filter evaluates the copy number at touchable history depth zero. An empty
copy-number list accepts all copies.

## Build-system impact

No project-specific build paths, generated binaries, or local environment
configuration are part of this contribution. The implementation relies on the
existing OpenGATE core source-discovery and module-registration mechanisms.

Because the change adds C++ and pybind11 code, rebuilding `opengate_core` is
required. A Python-only installation using an older compiled core will not
provide the new mesh builder or copy-number filter.

## Validation requirements

Before submission to upstream OpenGATE, the implementation should be rebased
onto the current `master` branch and validated with:

- a clean C++ core build;
- Python import and registration checks;
- direct `TetrahedralMesh` construction;
- MRCP_AF and MRCP_AM construction;
- custom `.node`, `.ele`, and `.material` filenames;
- material, visibility, and overlap checks;
- copy-number-filtered energy-deposition scoring; and
- representative single-thread and multi-thread runs.

Any binding already provided by the target upstream version should be removed
from this change during the rebase to avoid duplicate registrations.

## OpenGATE 10.1.1 validation

The following checks were completed on macOS arm64 with Python 3.12.12,
Geant4 11.4.0, and ITK 5.2.1:

- Python syntax compilation for all modified Python modules;
- a clean CMake configure and full `opengate_core` build;
- import checks for `G4Tet`, `GateCopyNumberFilter`, and
  `build_tetrahedral_mesh_from_tetgen`;
- Python registration of `TetrahedralMeshVolume` and `CopyNumberFilter`;
- a one-tetrahedron geometry/material/filter/dose integration run;
- a two-thread one-tetrahedron integration run;
- MRCP_AM default-filename selection and custom-filename preservation using a
  minimal TetGen fixture;
- full MRCP_AF geometry initialization with 1,279,642 nodes and 8,582,677
  tetrahedra; and
- a five-event MRCP_AF transport run with aggregate and per-region dose actors.

The full MRCP_AF run selected 48,012 tetrahedra for heart/lung scoring and
created five dose actors. The right-lung and aggregate outputs contained the
same three nonzero voxels and the same total deposited energy, confirming
consistent copy-number filtering for that run.

A complete MRCP_AM geometry/transport run remains pending because the full
MRCP_AM dataset was not available in the local test environment. Validation
against the current upstream `master` branch also remains pending.

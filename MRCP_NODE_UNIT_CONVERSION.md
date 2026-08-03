# MRCP Node Coordinate Unit Conversion

## Decision

MRCP TetGen `.node` coordinates are expressed in centimetres, while Geant4
uses millimetres as its base length unit. The MRCP geometry must therefore
interpret node coordinates as `cm` when they are parsed. This is a unit
conversion, not a user-configurable phantom scale.

The measured `MRCP_AF.node` spans are:

```text
raw X span:  50.539004
raw Y span:  27.219868
raw Z span: 163.017440
```

Interpreting these values as centimetres gives a physically plausible adult
phantom of approximately 505 x 272 x 1630 mm. Interpreting them directly as
millimetres would make the phantom ten times too small.

## Implementation

The shared C++ reader now accepts the input coordinate unit:

```cpp
read_node_file(node_path, input_length_unit)
```

Coordinates are converted to Geant4 internal units during parsing:

```cpp
NodeRec{x * input_length_unit,
        y * input_length_unit,
        z * input_length_unit}
```

The generic TetGen builder preserves its existing API and behavior by passing:

```cpp
scale * mm
```

The MRCP-specific builder has no scale argument and passes:

```cpp
cm
```

The resulting `NodeRec` values are already in Geant4 internal length units.
Mesh-center and `G4ThreeVector` construction therefore use those values
directly without another multiplication.

The Python MRCP volume calls:

```python
g4.build_mrcp_tetrahedral_mesh_from_tetgen(...)
```

The Python envelope parser explicitly interprets the same input coordinates as
centimetres using `g4_units.cm / g4_units.mm`. The user-facing
`phantom_scale` JSON setting, the `add_mrcp_phantom(scale=...)` argument, and
the stored phantom scale were removed.

The phantom world translation follows the same convention: the center derived
from `.node` coordinates is multiplied by `cm`, while `phantom_z_mm` remains an
explicit millimetre offset. This avoids mixing the two input units.

## Modified files

- `core/opengate_core/opengate_lib/GateTetrahedralMeshParameterisation.cpp`
- `core/opengate_core/opengate_lib/GateTetrahedralMeshParameterisation.h`
- `core/opengate_core/opengate_lib/pyGateTetrahedralMesh.cpp`
- `opengate/geometry/solids.py`
- `opengate/geometry/volumes.py`
- `opengate/contrib/mrcp/mrcp.py`
- `opengate/contrib/mrcp/mrcp_utils.py`

## Compatibility

The general-purpose `build_tetrahedral_mesh_from_tetgen` binding remains
available with its original `scale` argument. Only the MRCP-specific path fixes
the input coordinate unit to centimetres.

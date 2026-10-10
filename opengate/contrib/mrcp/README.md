# Tetrahedral MRCP phantom support

This contribution demonstrates how to construct an OpenGATE geometry from
TetGen tetrahedral-mesh files used by MRCP-style computational phantoms.
The mesh is represented by one parameterised Geant4 daughter volume whose
copies use individual `G4Tet` solids.

## Input files

`TetrahedralMeshVolume` reads four files:

- `*.node`: TetGen node coordinates. MRCP node coordinates are interpreted in
  centimetres and converted to Geant4 length units while they are read.
- `*.ele`: four node indices and one region ID for each tetrahedron.
- `*.material`: material density and elemental mass fractions, together with
  the region-to-material mapping.
- `*_colour.dat`: optional region ID followed by red, green, blue, and alpha
  values in the range `[0, 1]`.

The node reader accepts complete zero-based (`0..N-1`) or one-based (`1..N`)
indices. It rejects duplicate, incomplete, mixed, and out-of-range indices.

## Minimal example

```python
from pathlib import Path

import opengate as gate

data_dir = Path("opengate/contrib/mrcp")

sim = gate.Simulation()
sim.world.size = [2 * gate.g4_units.m] * 3
sim.world.material = "G4_Galactic"

phantom = sim.add_volume("TetrahedralMesh", "phantom_tetmesh")
phantom.mother = "world"
phantom.material = "G4_Galactic"
phantom.node_file = str(data_dir / "simple.node")
phantom.ele_file = str(data_dir / "simple.ele")
phantom.material_file = str(data_dir / "simple.material")
phantom.color_file = str(data_dir / "simple_colour.dat")
phantom.default_material = "G4_Galactic"
phantom.check_overlaps = True

sim.run()
```

Run `mrcp_simple.py` to initialize the example with Qt visualization enabled.
No particle source is configured because the script is a geometry example.

## Synthetic datasets

The directory contains synthetic, non-anatomical data so the implementation
can be demonstrated without redistributing a human phantom:

- `simple.*`: a separated sphere approximation, cube, and regular
  tetrahedron using region IDs 100, 200, and 300.
- `letter.*`: a separated three-dimensional `GATE` label using region IDs
  400, 500, 600, and 700.

`keep_regions` may be set to a list of region IDs to retain selected regions.
Unmapped tetrahedra use `default_material`. Visualization colors and
visibility are taken from the color file when provided.

## Copy-number filtering

Each parameterised tetrahedron has its own Geant4 copy number. Actors can use
`CopyNumberFilter` when scoring must be restricted to selected tetrahedron
copies:

```python
copy_filter = sim.add_filter("CopyNumberFilter", "selected_tetrahedra")
copy_filter.copy_numbers = [0, 1, 2]
```

An empty `copy_numbers` list disables copy-number selection and accepts all
valid steps.

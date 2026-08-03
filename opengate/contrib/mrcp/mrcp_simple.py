"""Minimal MRCP tetrahedral-phantom geometry example."""

from pathlib import Path

import opengate as gate


# All MRCP input files are expected to be in the same directory as this script.
data_dir = Path(__file__).resolve().parent

# Create a single-threaded simulation and a vacuum world large enough for MRCP.
sim = gate.Simulation()
sim.number_of_threads = 1

sim.world.size = [2 * gate.g4_units.m] * 3
sim.world.material = "G4_Galactic"

# Open the Geant4 Qt viewer when the simulation starts.
sim.visu = True
sim.visu_type = "qt"

# Create the MRCP tetrahedral mesh directly from the TetGen input files.
# MRCP .node coordinates are stored in cm; the MRCP C++ reader converts them
# to Geant4's mm unit with a fixed factor of 10, so no Python scale is needed.
phantom = sim.add_volume("TetrahedralMesh", "phantom_tetmesh")
phantom.mother = "world"
phantom.material = "G4_Galactic"
phantom.node_file = str(data_dir / "sample.node")
phantom.ele_file = str(data_dir / "sample.ele")
phantom.material_file = str(data_dir / "sample.material")
# Assign visualization colors to the material/organ indices.
phantom.color_file = str(data_dir / "sample_colour.dat")

# Use vacuum for any tetrahedron whose material index is not defined.
phantom.default_material = "G4_Galactic"
phantom.pv_name = "phantom_tetmesh_env"
phantom.check_overlaps = False

# Initialize the geometry and open the Qt visualization window.
sim.run()

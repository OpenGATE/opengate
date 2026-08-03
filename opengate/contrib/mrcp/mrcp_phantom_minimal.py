import opengate as gate
from opengate.contrib.phantoms.mrcp import add_mrcp_phantom


sim = gate.Simulation()
sim.number_of_threads = 1

sim.world.size = [2 * gate.g4_units.m] * 3
sim.world.material = "G4_Galactic"

sim.visu = True
sim.visu_type = "qt"

add_mrcp_phantom(
    sim,
    name="phantom_tetmesh",
    phantom_type="adult_male",
    node_file="MRCP_AF_heart_lung.node",
    ele_file="MRCP_AF_heart_lung.ele",
    material_file="MRCP_AF_heart_lung.material",
    color_file="colour.dat",
    show_all_organs=True,
    scale=10.0,
)

sim.run()

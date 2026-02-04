"""First test with OpenGATE.

* @File    :   sim_001.py
* @Time    :   2025/12/22 14:59:33
* @Author  :   Marc Ballestero Ribó
* @Version :   0
* @Contact :   marcballesteroribo@gmail.com
* @License :   GNU GPL v3.0
* @Desc    :   None
"""

import opengate as gate


if __name__ == "__main__":
    sim = gate.Simulation()
    sim.g4_verbose = True
    sim.visu = True
    sim.visu_type = "qt"
    sim.number_of_threads = -1
    sim.output_dir = "output"

    world = sim.world
    world.size = [ 5 * gate.g4_units.m, 5 * gate.g4_units.m, 5 * gate.g4_units.m]
    world.material = "G4_Galactic"

    box = sim.add_volume("BoxVolume", "box")
    box.size = [1 * gate.g4_units.m, 1 * gate.g4_units.m, 1 * gate.g4_units.m]
    box.material = "G4_Galactic"
    box.mother = "world"

    field = gate.geometry.fields.MagneticField(name="b_field")
    box.add_field(field)

    print(f"Fields in volume manager: {sim.volume_manager.fields}")
    print(f"Fields in box volume: {box.g4_field_manager}")

    sim.run()


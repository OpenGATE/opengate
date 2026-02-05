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

    field = gate.geometry.fields.UniformMagneticField(
        name="mag_field",
        field_vector = [1*gate.g4_units.tesla, 2*gate.g4_units.tesla, 0],
    )

    # field = gate.geometry.fields.QuadrupoleMagneticField(
    #     name="quad_field",
    #     gradient = 10 * gate.g4_units.tesla / gate.g4_units.meter,
    # )
    box.add_field(field)


    source = sim.add_source("IonPencilBeamSource", "g2_source")
    source.particle = "proton"
    source.n = 10
    source.energy.type = "gauss"
    source.energy.mono = 70.0 * gate.g4_units.MeV
    source.energy.sigma_gauss = 0.3 * source.energy.mono
    source.position.type = "point"
    source.position.translation = [
        0 * gate.g4_units.cm,
        0 * gate.g4_units.cm,
        -100 * gate.g4_units.cm,
    ]

    source.direction.partPhSp_x = [
    2.3335754 * gate.g4_units.mm,
    2.3335754 * gate.g4_units.mrad,
    0.00078728 * gate.g4_units.mm * gate.g4_units.mrad,
    0.,
    ]
    source.direction.partPhSp_y = [
        1.96433431 * gate.g4_units.mm,
        0.00079118 * gate.g4_units.mrad,
        0.00249161 * gate.g4_units.mm * gate.g4_units.mrad,
        0,
    ]

    sim.run()


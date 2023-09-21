#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
import os

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "gate_test044_pbs")
    output_path = paths.output / "output_test044_weight"

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 123654789
    ui.random_engine = "MersenneTwister"

    # units
    km = gate.g4_units("km")
    cm = gate.g4_units("cm")
    mm = gate.g4_units("mm")
    um = gate.g4_units("um")
    MeV = gate.g4_units("MeV")
    Bq = gate.g4_units("Bq")
    nm = gate.g4_units("nm")
    deg = gate.g4_units("deg")
    mrad = gate.g4_units("mrad")

    # add a material database
    sim.add_material_database(paths.gate_data / "HFMaterials2014.db")

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]

    ## FIRST SOURCE + DETECTOR ##
    # waterbox
    # translation and rotation like in the Gate macro
    waterbox1 = sim.add_volume("Box", "waterbox1")
    waterbox1.size = [10 * cm, 10 * cm, 105 * cm]
    waterbox1.translation = [0 * cm, 0 * cm, 52.5 * cm]
    waterbox1.material = "Vacuum"
    waterbox1.color = [0, 0, 1, 1]

    # phantoms
    m = Rotation.identity().as_matrix()

    phantom = sim.add_volume("Box", "phantom_a_1")
    phantom.mother = "waterbox1"
    phantom.size = [100 * mm, 100 * mm, 50 * mm]
    phantom.translation = [0 * mm, 0 * mm, -500 * mm]
    phantom.rotation = m
    phantom.material = "G4_AIR"
    phantom.color = [1, 0, 1, 1]

    # default source for tests (from test42)
    source = sim.add_source("PencilBeamSource", "mysource1")
    source.mother = "waterbox1"
    source.energy.mono = 60 * MeV
    source.particle = "proton"
    source.position.type = "disc"  # pos = Beam, shape = circle + sigma
    source.position.translation = [0 * mm, 0 * mm, -52.5 * cm]
    # rotate the disc, equiv to : rot1 0 1 0 and rot2 0 0 1
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 20000
    source.weight = 1
    source.direction.partPhSp_x = [
        2.3335754 * mm,
        2.3335754 * mrad,
        0.00078728 * mm * mrad,
        0,
    ]
    source.direction.partPhSp_y = [
        1.96433431 * mm,
        0.00079118 * mrad,
        0.00249161 * mm * mrad,
        0,
    ]

    # add dose actor
    dose = sim.add_actor("DoseActor", "doseInYZ_1")
    filename = "phantom_a_1.mhd"
    dose.output = output_path / filename
    dose.mother = "phantom_a_1"
    dose.size = [250, 250, 1]
    dose.spacing = [0.4, 0.4, 2]
    dose.hit_type = "random"

    ## SECOND SOURCE + DETECTOR ##
    # waterbox
    # translation and rotation like in the Gate macro
    waterbox2 = sim.add_volume("Box", "waterbox2")
    waterbox2.size = [10 * cm, 10 * cm, 105 * cm]
    waterbox2.translation = [30 * cm, 0 * cm, 52.5 * cm]
    waterbox2.material = "Vacuum"
    waterbox2.color = [0, 0, 1, 1]

    # phantoms
    m = Rotation.identity().as_matrix()

    phantom2 = sim.add_volume("Box", "phantom_a_2")
    phantom2.mother = "waterbox2"
    phantom2.size = [100 * mm, 100 * mm, 50 * mm]
    phantom2.translation = [0 * mm, 0 * mm, -500 * mm]
    phantom2.rotation = m
    phantom2.material = "G4_AIR"
    phantom2.color = [1, 0, 1, 1]

    # default source for tests (from test42)
    source2 = sim.add_source("PencilBeamSource", "mysource2")
    source2.mother = "waterbox2"
    source2.energy.mono = 60 * MeV
    source2.particle = "proton"
    source2.position.type = "disc"  # pos = Beam, shape = circle + sigma
    source2.position.translation = [0 * mm, 0 * mm, -52.5 * cm]
    # rotate the disc, equiv to : rot1 0 1 0 and rot2 0 0 1
    source2.direction.type = "momentum"
    source2.direction.momentum = [0, 0, 1]
    source2.n = 20000
    source2.weight = 2
    source2.direction.partPhSp_x = [
        2.3335754 * mm,
        2.3335754 * mrad,
        0.00078728 * mm * mrad,
        0,
    ]
    source2.direction.partPhSp_y = [
        1.96433431 * mm,
        0.00079118 * mrad,
        0.00249161 * mm * mrad,
        0,
    ]

    # add dose actor
    dose2 = sim.add_actor("DoseActor", "doseInYZ_2")
    filename = "phantom_a_2.mhd"
    dose2.output = output_path / filename
    dose2.mother = "phantom_a_2"
    dose2.size = [250, 250, 1]
    dose2.spacing = [0.4, 0.4, 2]
    dose2.hit_type = "random"

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # physics
    sim.physics_manager.physics_list_name = "FTFP_INCLXX_EMZ"
    sim.physics_manager.global_production_cuts.all = 1000 * km

    print(sim.dump_sources())

    # create output dir, if it doesn't exist
    if not os.path.isdir(output_path):
        os.mkdir(output_path)

    # start simulation
    sim.run()

    # print results at the end
    stat = sim.output.get_actor("Stats")
    print(stat)

    # ----------------------------------------------------------------------------------------------------------------
    # tests

    # energy deposition: we expect the edep from source two
    # to be double the one of source one

    print("\nDifference for EDEP")
    mhd_1 = "phantom_a_1.mhd"
    mhd_2 = "phantom_a_2.mhd"
    test = True
    # test = gate.assert_images(
    #     output_path / mhd_1,
    #     output_path / mhd_2,
    #     stat,
    #     axis="x",
    #     tolerance=50,
    #     ignore_value=0,
    # )
    fig1 = gate.create_2D_Edep_colorMap(output_path / mhd_1, show=False)
    fig2 = gate.create_2D_Edep_colorMap(output_path / mhd_2, show=False)

    # Total Edep
    is_ok = (
        gate.test_weights(
            source2.weight / source.weight,
            output_path / mhd_1,
            output_path / mhd_2,
            thresh=0.2,
        )
        and test
    )

    gate.test_ok(is_ok)

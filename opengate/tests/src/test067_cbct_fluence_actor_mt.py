#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test067", "test067")

    sim = gate.Simulation()

    sim.visu = False
    sim.visu_type = "vrml"
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 321654
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    cm3 = gate.g4_units.cm3
    keV = gate.g4_units.keV
    MeV = gate.g4_units.MeV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    gcm3 = gate.g4_units.g / cm3

    # world
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [20 * cm, 20 * cm, 20 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 15 * cm]
    waterbox.material = "G4_WATER"

    # CBCT gantry source
    gantry = sim.add_volume("Box", "CBCT_gantry")
    gantry.size = [0.2 * m, 0.2 * m, 0.2 * m]
    gantry.translation = [1000 * mm, 0, 0]
    gantry.material = "G4_AIR"
    gantry.color = [0, 1, 1, 1]

    # CBCT detector plane
    detector_plane = sim.add_volume("Box", "CBCT_detector_plane")
    detector_plane.size = [10 * mm, 1409.6 * mm, 1409.6 * mm]
    detector_plane.translation = [-536 * mm, 0, 0]
    detector_plane.material = "G4_AIR"
    detector_plane.color = [1, 0, 0, 1]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option1"
    sim.physics_manager.set_production_cut("world", "all", 10 * mm)

    # actor
    detector_actor = sim.add_actor("FluenceActor", "detector_actor")
    detector_actor.attached_to = detector_plane
    detector_actor.output_filename = "fluence.mhd"
    detector_actor.spacing = [10 * mm, 5 * mm, 5 * mm]
    detector_actor.size = [1, 100, 100]
    detector_actor.output_coordinate_system = "local"

    # source
    source = sim.add_source("GenericSource", "mysource")
    source.mother = gantry.name
    source.particle = "gamma"
    source.energy.mono = 60 * keV
    source.position.type = "box"
    source.position.size = [1 * nm, 2 * 8 * mm, 2 * 8 * mm]
    source.direction.type = "focused"
    # FIXME warning in world coord ! Should be in mother coord system
    source.direction.focus_point = [gantry.translation[0] - 60 * mm, 0, 0]
    if sim.visu:
        source.n = 100
    else:
        source.n = 50000 / sim.number_of_threads

    # statistics
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = "stats.txt"

    # run
    sim.run()

    # print output statistics
    print(stats)
    out_path = detector_actor.get_output_path()

    # check images
    is_ok = utility.assert_images(
        paths.gate_output / "detector.mhd",
        out_path,
        stats,
        tolerance=44,
        axis="y",
    )

    utility.test_ok(is_ok)

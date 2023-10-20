#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test029_volume_time_rotation", "test030"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.random_seed = 983456

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    um = gate.g4_units.um
    nm = gate.g4_units.nm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.second

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.translation = [1 * cm, 2 * cm, 3 * cm]
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.mother = "fake"
    waterbox.size = [20 * cm, 20 * cm, 20 * cm]
    waterbox.translation = [-3 * cm, -2 * cm, -1 * cm]
    waterbox.rotation = Rotation.from_euler("y", -20, degrees=True).as_matrix()
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]

    # physics
    sim.set_production_cut("world", "all", 700 * um)

    # default source for tests
    # the source is fixed at the center, only the volume will move
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 150 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.radius = 5 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 30000 * Bq

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = paths.output / "test030-edep.mhd"
    dose.mother = "waterbox"
    dose.size = [99, 99, 99]
    mm = gate.g4_units.mm
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.translation = [2 * mm, 3 * mm, -2 * mm]
    dose.uncertainty = True

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    s.output = paths.output / "stats030.txt"

    # motion
    motion = sim.add_actor("MotionVolumeActor", "Orbiting")
    motion.mother = fake.name
    motion.translations = []
    motion.rotations = []
    sim.run_timing_intervals = []
    n = 3
    start = 0
    gantry_rotation = start
    end = 1 * sec / n
    for r in range(n):
        t, rot = gate.geometry.utility.get_transform_orbiting(
            fake.translation, "Y", gantry_rotation
        )
        motion.translations.append(t)
        motion.rotations.append(rot)
        sim.run_timing_intervals.append([start, end])
        gantry_rotation += 20
        start = end
        end += 1 * sec / n

    # start simulation
    output = sim.run()

    # print results at the end
    stat = sim.output.get_actor("Stats")
    print(stat)

    dose = sim.output.get_actor("dose")
    print(dose)

    # tests
    stats_ref = utility.read_stat_file(paths.output_ref / "stats030.txt")
    is_ok = utility.assert_stats(stat, stats_ref, 0.11)

    print()
    gate.exception.warning("Difference for EDEP")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test030-edep.mhd",
            paths.output / "test030-edep.mhd",
            stat,
            tolerance=30,
            ignore_value=0,
        )
        and is_ok
    )

    print("\nDifference for uncertainty")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test030-edep_uncertainty.mhd",
            paths.output / "test030-edep_uncertainty.mhd",
            stat,
            tolerance=15,
            ignore_value=1,
        )
        and is_ok
    )

    utility.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import opengate.contrib.phantoms.nemaiec as gate_iec

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test015")

    # create the simulation
    sim = gate.Simulation()

    # units
    MeV = gate.g4_units.MeV
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    cm3 = gate.g4_units.cm3
    Bq = gate.g4_units.Bq
    BqmL = Bq / cm3

    # main options
    ui = sim.user_info
    # ui.visu = True
    # ui.visu_type = "qt"
    ui.check_volumes_overlap = True
    ui.random_seed = 123654987

    # physics
    p = sim.get_physics_user_info()
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 10 * mm)

    # world size
    world = sim.world
    world.size = [0.5 * m, 0.5 * m, 0.5 * m]

    # add an iec phantom
    # rotation 180 around X to be like in the iec 61217 coordinate system
    iec_phantom = gate_iec.add_iec_phantom(sim)

    # box around
    b = sim.add_volume("Box", "box")
    b.size = [33 * cm, 33 * cm, 25 * cm]
    iec_phantom.mother = b.name

    # add sources for all spheres
    a = 100 * BqmL
    activity_Bq_mL = [10 * a, 2 * a, 3 * a, 4 * a, 5 * a, 6 * a]
    sources = gate_iec.add_spheres_sources(
        sim, iec_phantom.name, "sources", "all", activity_Bq_mL, verbose=True
    )
    for source in sources:
        source.particle = "alpha"
        source.energy.type = "mono"
        source.energy.mono = 100 * MeV

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output = paths.output / "test015_iec_2_stats.txt"

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = paths.output / "test015_iec_2.mhd"
    dose.attached_to = iec_phantom.name
    dose.size = [100, 100, 100]
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]

    # start
    sim.run()

    # compare stats
    stats = sim.get_actor("stats")
    stats_ref = utility.read_stat_file(paths.output_ref / "test015_iec_2_stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.03)

    # compare images
    f = paths.output / "test015_iec_2.mhd"
    im_ok = utility.assert_images(
        paths.output_ref / "test015_iec_2.mhd",
        dose.output,
        stats,
        axis="x",
        tolerance=40,
        ignore_value=0,
        sum_tolerance=2,
    )

    is_ok = is_ok and im_ok
    utility.test_ok(is_ok)

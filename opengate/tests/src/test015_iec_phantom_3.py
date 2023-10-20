#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
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
    ui.check_volumes_overlap = True
    ui.random_seed = 123654987

    # physics
    p = sim.get_physics_user_info()
    p.physics_list_name = "G4EmStandardPhysics_option3"
    sim.set_production_cut("world", "all", 10 * mm)

    # world size
    world = sim.world
    world.size = [0.5 * m, 0.5 * m, 0.5 * m]

    # add an iec phantom
    iec_phantom = gate_iec.add_iec_phantom(sim)

    # add sources for all central cylinder
    a = 20 * BqmL
    bg1 = gate_iec.add_central_cylinder_source(
        sim, iec_phantom.name, "bg1", a * 5, verbose=True
    )
    bg1.particle = "alpha"
    bg1.energy.type = "mono"
    bg1.energy.mono = 100 * MeV

    # add background source
    bg2 = gate_iec.add_background_source(sim, iec_phantom.name, "bg2", a, verbose=True)
    bg2.particle = "alpha"
    bg2.energy.type = "mono"
    bg2.energy.mono = 100 * MeV

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output = paths.output / "test015_iec_3_stats.txt"

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = paths.output / "test015_iec_3.mhd"
    dose.mother = iec_phantom.name
    dose.size = [100, 100, 100]
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]

    # start
    sim.run()

    # compare stats
    stats = sim.output.get_actor("stats")
    stats_ref = utility.read_stat_file(paths.output_ref / "test015_iec_3_stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.02)

    # compare images
    f = paths.output / "test015_iec_3.mhd"
    im_ok = utility.assert_images(
        paths.output_ref / "test015_iec_3.mhd",
        dose.output,
        stats,
        axis="y",
        tolerance=86,
        ignore_value=0,
        sum_tolerance=2,
    )

    is_ok = is_ok and im_ok
    utility.test_ok(is_ok)

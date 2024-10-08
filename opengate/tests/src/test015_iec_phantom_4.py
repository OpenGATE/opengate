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
    sim.check_volumes_overlap = True
    sim.random_seed = "auto"  # 123456789
    sim.output_dir = paths.output
    sim.progress_bar = True

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 10 * mm)

    # world size
    sim.world.size = [0.5 * m, 0.5 * m, 0.5 * m]

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

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = "test015_iec_4_stats.txt"

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.edep.output_filename = "test015_iec_4.mhd"
    dose.attached_to = iec_phantom
    dose.size = [150, 150, 150]
    dose.spacing = [3 * mm, 3 * mm, 3 * mm]

    # start
    sim.run()

    # compare stats
    stats_ref = utility.read_stat_file(paths.output_ref / "test015_iec_4_stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.02)

    # compare images
    dose = sim.get_actor("dose")
    f = paths.output / "test015_iec_4.mhd"
    im_ok = utility.assert_images(
        paths.output_ref / "test015_iec_4.mhd",
        dose.edep.get_output_path(),
        stats,
        axis="y",
        tolerance=50,
        ignore_value=0,
        sum_tolerance=1.0,
        sad_profile_tolerance=3.0,
    )

    is_ok = is_ok and im_ok
    utility.test_ok(is_ok)

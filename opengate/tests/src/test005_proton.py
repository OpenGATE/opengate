#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, gate_folder="gate_test005_proton")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_engine = "MersenneTwister"

    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    # add a simple volume
    waterbox = sim.add_volume("Box", "Waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    # default source for tests
    # FiXME warning ref not OK (cppSource is not exactly the same)
    source = sim.add_source("GenericSource", "Default")
    source.particle = "proton"
    source.energy.mono = 150 * MeV
    source.position.radius = 10 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 20000

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # verbose (WARNING : ui.g4_verbose must be True !)
    sim.apply_g4_command("/tracking/verbose 0")
    # sim.apply_g4_command("/run/verbose 2")
    # sim.apply_g4_command("/event/verbose 2")
    # sim.apply_g4_command("/tracking/verbose 1")

    print(sim.dump_sources())

    # start simulation
    sim.run()

    # get results
    stats = sim.output.get_actor("Stats")
    print("Simulation seed:", sim.output.current_random_seed)
    print(stats)

    # gate_test5_proton
    # Gate mac/main.mac
    print("-" * 80)
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.15)

    utility.test_ok(is_ok)

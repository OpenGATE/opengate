#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.tests.utility as utility
from opengate.utility import g4_units

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test004_simulation_stats_actor"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.running_verbose_level = 0
    sim.visu = False
    sim.number_of_threads = 5
    # special debug mode : force MT even with one single thread
    sim.force_multithread_mode = True
    sim.random_engine = "MixMaxRng"
    sim.random_seed = "auto"

    """
        Warning: we can only see the speed up of the MT mode for large nb of particles (>2e6)
    """

    # set the world size like in the Gate macro
    m = g4_units.m
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    # add a simple waterbox volume
    waterbox = sim.add_volume("Box", "Waterbox")
    cm = g4_units.cm
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    # physic list
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    um = g4_units.um
    global_cut = 700 * um
    sim.physics_manager.global_production_cuts.gamma = global_cut
    sim.physics_manager.global_production_cuts.electron = global_cut
    sim.physics_manager.global_production_cuts.positron = global_cut
    sim.physics_manager.global_production_cuts.proton = global_cut

    # default source for tests
    keV = g4_units.keV
    mm = g4_units.mm
    Bq = g4_units.Bq
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 200000 / sim.number_of_threads

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # start simulation
    # sim.g4_commands_after_init.append("/run/verbose 0")
    # sim.g4_commands_after_init.append("/run/eventModulo 5000 1")
    sim.run()

    # get results
    print(stats)
    print("track type", stats.counts.track_types)

    # gate_test4_simulation_stats_actor
    # Gate mac/main.mac
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    stats_ref.counts.runs = sim.number_of_threads
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.01)

    utility.test_ok(is_ok)

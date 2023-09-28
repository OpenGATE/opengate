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
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = True
    ui.visu_type = "gdml"
    ui.visu_filename = "geant4VisuFile.gdml"
    ui.visu_verbose = True
    ui.number_of_threads = 1
    ui.random_engine = "MersenneTwister"
    ui.random_seed = "auto"

    # set the world size like in the Gate macro
    m = g4_units.m
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]

    # add a simple waterbox volume
    waterbox = sim.add_volume("Box", "Waterbox")
    cm = g4_units.cm
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    # default source for tests
    keV = g4_units.keV
    mm = g4_units.mm
    Bq = g4_units.Bq
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 200000 * Bq

    # runs
    sec = g4_units.second
    sim.run_timing_intervals = [[0, 0.5 * sec]]

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # start simulation
    # sim.apply_g4_command("/run/verbose 1")
    sim.run()

    stats = sim.output.get_actor("Stats")
    stats.counts.run_count = 1

    # gate_test4_simulation_stats_actor
    # Gate mac/main.mac
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    # is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.03)

    # utility.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import pathlib

if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.number_of_threads = 2

    # set the world size like in the Gate macro
    m = gate.g4_units.m
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]

    # add a simple volume
    waterbox = sim.add_volume("Box", "Waterbox")
    cm = gate.g4_units.cm
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    # physic list
    # print('Phys lists :', sim.get_available_physicLists())

    # default source for tests
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 200000 * Bq / sim.user_info.number_of_threads

    # two runs
    sec = gate.g4_units.second
    sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1 * sec]]

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # verbose
    # sim.g4_apply_command('/tracking/verbose 0')
    # sim.g4_com("/run/verbose 2")
    # sim.g4_com("/event/verbose 2")
    # sim.g4_com("/tracking/verbose 1")

    # start simulation
    sim.run()

    stats = sim.output.get_actor("Stats")
    print(stats)
    print("-" * 80)

    # gate_test4_simulation_stats_actor
    # Gate mac/main.mac
    stats_ref = utility.read_stat_file(
        pathFile
        / ".."
        / "data"
        / "gate"
        / "gate_test004_simulation_stats_actor"
        / "output"
        / "stat.txt"
    )
    stats_ref.counts.run_count = sim.user_info.number_of_threads * len(
        sim.run_timing_intervals
    )
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.03)
    utility.test_ok(is_ok)

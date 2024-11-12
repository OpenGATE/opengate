#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test004_simulation_stats_actor"
    )
    sim = gate.Simulation()

    m = g4_units.m
    cm = g4_units.cm
    keV = g4_units.keV
    mm = g4_units.mm
    um = g4_units.um
    Bq = g4_units.Bq

    waterbox = sim.add_volume("Box", "Waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 200000

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # run
    sim.run(start_new_process=True)
    print(stats)

    # Comparison with gate simulation
    # gate_test4_simulation_stats_actor
    # Gate mac/main.mac
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.01)

    utility.test_ok(is_ok)

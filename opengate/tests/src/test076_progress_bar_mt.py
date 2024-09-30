#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests.utility import (
    get_default_test_paths,
    test_ok,
    print_test,
)
from opengate.utility import g4_units
from opengate.managers import Simulation

if __name__ == "__main__":
    paths = get_default_test_paths(__file__, "gate_test004_simulation_stats_actor")

    # sim
    sim = Simulation()
    sim.progress_bar = True
    sim.number_of_threads = 2
    sim.random_seed = 321654
    #   sim.running_verbose_level = EVENT

    # units
    m = g4_units.m
    cm = g4_units.cm
    keV = g4_units.keV
    mm = g4_units.mm
    um = g4_units.um
    Bq = g4_units.Bq
    s = g4_units.s

    # world
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    # wb
    waterbox = sim.add_volume("Box", "Waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    # phys
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"

    # src
    source = sim.add_source("GenericSource", "s1")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    # source.n = 200000
    source.activity = 100000 * Bq / sim.number_of_threads

    # src
    source = sim.add_source("GenericSource", "s2")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 100000 / sim.number_of_threads

    # src
    source = sim.add_source("GenericSource", "s3")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 100000 * Bq / sim.number_of_threads
    source.half_life = 0.5 * s

    # stats
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # go
    sim.run_timing_intervals = [
        [0, 1 * s],
        [1.5 * s, 3.0 * s],
        # Watch out : there is (on purpose) a 'hole' in the timeline
        [3.5 * s, 5.5 * s],
    ]
    sim.run(start_new_process=True)

    stats = sim.get_actor("Stats")
    print(stats)

    # Comparison with gate simulation
    n1 = sim.expected_number_of_events
    n2 = stats.counts.events
    f = abs(n1 - n2) / n2
    is_ok = f < 0.01
    print()
    print_test(is_ok, f"Predicted nb of events = {n1}, real = {n2}: {f*100:.2f}%")

    test_ok(is_ok)

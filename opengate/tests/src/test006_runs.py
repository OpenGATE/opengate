#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.tests.utility as utility

if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.verbose_level = gate.logger.DEBUG
    sim.running_verbose_level = 0  # gate.EVENT
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 13241234
    gate.logger.log.debug(sim)

    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.second

    # add a simple volume
    waterbox = sim.add_volume("Box", "Waterbox")
    waterbox.size = [20 * cm, 20 * cm, 20 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 15 * cm]
    waterbox.material = "G4_WATER"

    # default source for tests
    source1 = sim.add_source("GenericSource", "source1")
    source1.particle = "proton"
    source1.energy.mono = 150 * MeV
    source1.position.radius = 10 * mm
    source1.direction.type = "momentum"
    source1.direction.momentum = [0, 0, 1]
    source1.n = 2000

    source2 = sim.add_source("GenericSource", "source2")
    source2.particle = "proton"
    source2.energy.mono = 120 * MeV
    source2.position.radius = 5 * mm
    source2.activity = 2000 * Bq  # 25 + 50 + 100
    source2.direction.type = "momentum"
    source2.direction.momentum = [0, 0, 1]
    source2.start_time = 0.25 * sec

    source3 = sim.add_source("GenericSource", "source3")
    source3.particle = "proton"
    source3.energy.mono = 150 * MeV
    source3.position.radius = 10 * mm
    source3.n = 2400
    source3.start_time = 0.50 * sec
    source3.direction.type = "momentum"
    source3.direction.momentum = [0, 0, 1]

    # Expected total of events
    # 100 + 175 + 120 = 395

    # debug: uncomment to remove one source
    # sim.source_manager.sources.pop('source1')
    # sim.source_manager.sources.pop('source2')
    # sim.source_manager.sources.pop('source3')

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # run timing test #1
    sim.run_timing_intervals = [
        [0, 0.5 * sec],
        [0.5 * sec, 1.0 * sec],
        # Watch out : there is (on purpose) a 'hole' in the timeline
        [1.5 * sec, 2.5 * sec],
    ]

    # print sources
    print(sim.source_manager.dump_sources())

    # start simulation
    sim.run()

    # print stats (useful comment isn't it ?)
    print(stats)

    stats_ref = gate.actors.miscactors.SimulationStatisticsActor(name="stat_ref")
    c = stats_ref.counts
    c.runs = 3
    c.events = 7800
    c.tracks = 37584  # 56394
    c.steps = 266582  # 217234
    # stats_ref.pps = 4059.6 3 3112.2
    c.duration = 1 / 4059.6 * 7800 * sec
    print("-" * 80)
    is_ok = utility.assert_stats(stats, stats_ref, 0.185)

    utility.test_ok(is_ok)

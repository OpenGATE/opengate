#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam

# set log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()
sim.set_g4_verbose(False)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456789)

cm = gam.g4_units('cm')

# add a simple volume
waterbox = sim.add_volume('Box', 'Waterbox')
waterbox.size = [20 * cm, 20 * cm, 20 * cm]
waterbox.translation = [0 * cm, 0 * cm, 15 * cm]
waterbox.material = 'G4_WATER'

# default source for tests
MeV = gam.g4_units('MeV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')
sec = gam.g4_units('second')
source1 = sim.add_source('Generic', 'source1')
source1.particle = 'proton'
source1.energy.mono = 150 * MeV
source1.position.radius = 10 * mm
source1.n = 100

source2 = sim.add_source('Generic', 'source2')
source2.particle = 'proton'
source2.energy.mono = 120 * MeV
source2.position.radius = 5 * mm
source2.activity = 100 * Bq  # 25 + 50 + 100
source2.start_time = 0.25 * sec

source3 = sim.add_source('Generic', 'source3')
source3.particle = 'proton'
source3.energy.mono = 150 * MeV
source3.position.radius = 10 * mm
source3.n = 120
source3.start_time = 0.50 * sec
source3.toto = 120  # raise a warning

# Expected total of events
# 100 + 175 + 60 = 335

# debug: uncomment to remove one source
# sim.source_manager.sources.pop('source1')
# sim.source_manager.sources.pop('source2')
# sim.source_manager.sources.pop('source3')

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# run timing test #1
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 0.5 * sec],
                            [0.5 * sec, 1.0 * sec],
                            # Watch out : there is (on purpose) a 'hole' in the timeline
                            [1.5 * sec, 2.5 * sec],
                            ]

# create G4 objects
sim.initialize()
print(sim.dump_sources())
print(sim.dump_sources(1))

# control log : INFO = each RUN, DEBUG = each Event
gam.source_log.setLevel(gam.EVENT)

# start simulation
sim.start()

stats = sim.get_actor('Stats')
print(stats)

stats_ref = gam.SimulationStatisticsActor('test')
stats_ref.set_run_count(3)
stats_ref.set_event_count(390)
stats_ref.set_track_count(6806)
stats_ref.set_step_count(24042)
# stats_ref.pps = 5178
stats_ref.duration = 0.07531865585 * sec
print('-' * 80)
gam.assert_stats(stats, stats_ref, 0.1)

gam.test_ok()

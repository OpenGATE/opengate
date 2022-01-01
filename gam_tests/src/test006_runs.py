#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam

# set log level
# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.verbose_level = gam.DEBUG
ui.running_verbose_level = 0  # gam.EVENT
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = 1
gam.log.debug(ui)

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
source1.direction.type = 'momentum'
source1.direction.momentum = [0, 0, 1]
source1.n = 1000

source2 = sim.add_source('Generic', 'source2')
source2.particle = 'proton'
source2.energy.mono = 120 * MeV
source2.position.radius = 5 * mm
source2.activity = 1000 * Bq  # 25 + 50 + 100
source2.direction.type = 'momentum'
source2.direction.momentum = [0, 0, 1]
source2.start_time = 0.25 * sec

source3 = sim.add_source('Generic', 'source3')
source3.particle = 'proton'
source3.energy.mono = 150 * MeV
source3.position.radius = 10 * mm
source3.n = 1200
source3.start_time = 0.50 * sec
source3.direction.type = 'momentum'
source3.direction.momentum = [0, 0, 1]
source3.toto = 120  # raise a warning

# Expected total of events
# 100 + 175 + 120 = 395

# debug: uncomment to remove one source
# sim.source_manager.sources.pop('source1')
# sim.source_manager.sources.pop('source2')
# sim.source_manager.sources.pop('source3')

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'Stats')
s.track_types_flag = True

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

# start simulation
sim.start()

stats = sim.get_actor('Stats')
print(stats)

stats_ref = gam.SimulationStatisticsActor()
c = stats_ref.counts
c.run_count = 3
c.event_count = 3900
c.track_count = 18792  # 56394
c.step_count = 133291  # 217234
# stats_ref.pps = 4059.6 3 3112.2
c.duration = 1 / 4059.6 * 3900 * sec
print('-' * 80)
is_ok = gam.assert_stats(stats, stats_ref, 0.15)

gam.test_ok(is_ok)

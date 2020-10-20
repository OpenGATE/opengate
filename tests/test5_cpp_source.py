#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from box import Box

gam.log.setLevel(gam.DEBUG)

# create the simulation
s = gam.Simulation()
s.set_g4_verbose(False)

# set random engine
s.set_g4_random_engine("MersenneTwister", 123456)

# add a simple volume
waterbox = s.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'G4_WATER'

# physic list
# print('Phys lists :', s.get_available_physicLists())

# default source for tests
source = s.add_source('TestProtonCpp', 'Default')
source.n = 2000

# add stat actor
stats = s.add_actor('SimulationStatisticsActor', 'Stats')

# create G4 objects
s.initialize()

print(s.dump_sources())
print('Simulation seed:', s.seed)
print(s.dump_volumes())

# verbose
s.g4_apply_command('/tracking/verbose 0')
# s.g4_com("/run/verbose 2")
# s.g4_com("/event/verbose 2")
# s.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.RUN)
s.start()

stats = s.actors_info.Stats.g4_actor
print(stats)

stats_ref = Box()
stats_ref.run_count = 1
stats_ref.event_count = 2000
stats_ref.track_count = 25332
stats_ref.step_count = 107073
stats_ref.pps = 3856
print('-' * 80)
gam.assert_stats(stats, stats_ref)

gam.test_ok()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from box import Box

gam.log.setLevel(gam.DEBUG)

# create the simulation
s = gam.Simulation()
s.set_g4_verbose(False)

# set random engine
s.set_g4_random_engine("MersenneTwister", 1234561)

cm = gam.g4_units('cm')
mm = gam.g4_units('mm')
MeV = gam.g4_units('MeV')

# add a simple volume
waterbox = s.add_volume('Box', 'Waterbox')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'G4_WATER'

# default source for tests
source = s.add_source('Generic', 'Default')  # FiXME warning ref not OK (cppSource not the same)
source.particle = 'proton'
source.energy.mono = 150 * MeV
source.position.radius = 10 * mm
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.n = 20000

# add stat actor
s.add_actor('SimulationStatisticsActor', 'Stats')

# create G4 objects
s.initialize()

print(s.dump_sources())
print('Simulation seed:', s.seed)

# verbose
s.apply_g4_command('/tracking/verbose 0')
# s.g4_com("/run/verbose 2")
# s.g4_com("/event/verbose 2")
# s.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.RUN)
s.start()

stats = s.get_actor('Stats')
print(stats)


# gate_test5_proton
# Gate mac/main.mac
print('-' * 80)
stats_ref = gam.read_stat_file('./gate_test5_proton/output/stat.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.11)

gam.test_ok(is_ok)

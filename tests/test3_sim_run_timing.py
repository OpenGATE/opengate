#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import gam_g4 as g4

gam.logging_conf(True)

# create the simulation
sim = gam.Simulation()
sim.enable_g4_verbose(False)

# set random engine
sim.set_random_engine("MersenneTwister", 123456)

cm = gam.g4_units('cm')

# fake volume
# fake = s.add_volume('Box', 'Fake')
# fake.size = [20 * cm, 20 * cm, 20 * cm]
# fake.translation = [0 * cm, 0 * cm, 15 * cm]
# fake.material = 'Air'

# add a simple volume
waterbox = sim.add_volume('Box', 'Waterbox')
waterbox.size = [20 * cm, 20 * cm, 20 * cm]
waterbox.translation = [0 * cm, 0 * cm, 15 * cm]
waterbox.material = 'Water'
# waterbox.mother = 'Fake'

# fake2 volume
# fake2 = s.add_volume('Box', 'Fake2')
# fake2.size = [15 * cm, 15 * cm, 15 * cm]
# fake2.material = 'Water'
# fake2.mother = 'Waterbox'

# physic list
# print('Phys lists :', s.get_available_physicLists())

# default source for tests
MeV = gam.g4_units('MeV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')
sec = gam.g4_units('second')
source1 = sim.add_source('TestProtonPy2', 'source1')
source1.energy = 150 * MeV
source1.diameter = 20 * mm
source1.n = 10
source2 = sim.add_source('TestProtonTime', 'source2')
source2.energy = 120 * MeV
source2.diameter = 10 * mm
source2.activity = 20 * Bq
source3 = sim.add_source('TestProtonPy2', 'source3')
source3.energy = 150 * MeV
source3.diameter = 20 * mm
source3.start_time = 0.6 * sec
source3.n = 3

# add stat actor
stats = sim.add_actor('SimulationStatistics', 'Stats')

# run timing test #1
sec = gam.g4_units('second')
print('sec', sec)
sim.run_time_intervals = [[0, 0.5 * sec], [0.5 * sec, 1 * sec]]  # one single run, start and stop at zero

# create G4 objects
sim.initialize()

for s in sim.sources_info.values():
    print('Source: ', s.g4_UserPrimaryGenerator)

print('Simulation seed:', sim.seed)
print(sim.dump_geometry_tree())

# verbose
sim.g4_com('/tracking/verbose 0')
# s.g4_com("/run/verbose 2")
# s.g4_com("/event/verbose 2")
# s.g4_com("/tracking/verbose 1")

# debug source
n = gam.get_estimated_total_number_of_events(sim)
print(f'Total event {n}')

# start simulation
sim.start()

for s in sim.sources_info.values():
    print('Source: ', s.g4_UserPrimaryGenerator)

stat = sim.actors_info.Stats
print('actor:', stat)
print(stat.g4_actor)
print('end.')

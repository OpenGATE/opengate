#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import gam_g4 as g4

gam.log.setLevel(gam.DEBUG)

# create the simulation
s = gam.Simulation()
s.set_g4_verbose(False)

# set random engine
s.set_g4_random_engine("MersenneTwister", 123456)

cm = gam.g4_units('cm')

# fake volume
# fake = s.add_volume('Box', 'Fake')
# fake.size = [20 * cm, 20 * cm, 20 * cm]
# fake.translation = [0 * cm, 0 * cm, 15 * cm]
# fake.material = 'Air'

# add a simple volume
waterbox = s.add_volume('Box', 'Waterbox')
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
source = s.add_source('TestProtonCpp', 'Default')
source.energy = 150 * MeV
source.diameter = 20 * mm
source.n = 20000

# add stat actor
stats = s.add_actor('SimulationStatistics', 'Stats')

dose = s.add_actor('Dose3', 'Dose')
dose.attachedTo = 'Waterbox'

# create G4 objects
s.initialize()

print('Simulation seed:', s.seed)
print(s.dump_geometry_tree())

print(gam.info_all_sources(s))


# verbose
s.g4_apply_command('/tracking/verbose 0')
# s.g4_com("/run/verbose 2")
# s.g4_com("/event/verbose 2")
# s.g4_com("/tracking/verbose 1")

# start simulation
s.start()

stat = s.actors_info.Stats
print('actor:', stat)
print(stat.g4_actor)
print(dose.g4_actor)
print('end.')

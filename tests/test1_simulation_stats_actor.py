#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import gam_g4 as g4

gam.logging_conf(True)

# create the simulation
s = gam.Simulation()
s.enable_g4_output(False)

# set random engine
s.set_random_engine("MersenneTwister", 12345678)

# add a simple volume
waterbox = s.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'Water'

# physic list
# print('Phys lists :', s.get_available_physicLists())

# default source for tests
source = s.add_source('Test', 'Default')

# add stat actor
stats = s.add_actor('SimulationStatistics', 'Stats')

# create G4 objects
s.initialize()

print('Simulation seed:', s.physics.seed)
print(s.dump_geometry_tree())

# verbose
s.g4_com('/tracking/verbose 0')
# s.g4_com("/run/verbose 2")
# s.g4_com("/event/verbose 2")
# s.g4_com("/tracking/verbose 1")

# start simulation
s.start()

stat = s.actors.Stats
print('actor:', stat)
print(stat.g4_actor)
print('end.')

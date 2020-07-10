#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam2
import gam
import gam_g4 as g4

# create the simulation
s = gam2.Simulation()

# set random engine
s.set_random_engine("MersenneTwister", 123456)

# add a simple volume
waterbox = s.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40*cm, 40*cm, 40*cm]
waterbox.translation = [0*cm, 0*cm, 25*cm]
waterbox.material = 'Water'

# test
# a = s.add_volume('Box', 'A')
# a.size = [5,5,5]
# a.mother = 'Waterbox'
# a.material = 'Water'
# a = s.add_volume('Box', 'B')
# a.size = [5,5,5]
# a.mother = 'World'
# a.material = 'Water'
# a = s.add_volume('Box', 'C')
# a.size = [5,5,5]
# a.mother = 'World'
# a.material = 'Water'

# default source for tests
source = s.add_source('Test', 'Default')

# add stat actor
stats = s.add_actor('SimulationStatistics', 'Stats')
stats.attachedTo = 'World'

# create G4 objects
print(s)
s.initialize()

# verbose
ui = g4.G4UImanager.GetUIpointer()
#ui.ApplyCommand("/run/verbose 2")
#ui.ApplyCommand("/event/verbose 2")
#ui.ApplyCommand("/tracking/verbose 1")

# start simulation
s.start()

stat = s.actors.Stats
print('actor:', stat)
print(stat.g4_actor)
print('end.')

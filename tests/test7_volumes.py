#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import gam_g4 as g4

gam.log.setLevel(gam.DEBUG)

# create the simulation
s = gam.Simulation()
s.enable_g4_verbose(False)

# set random engine
s.set_random_engine("MersenneTwister", 123456)

# add a simple volume
waterbox = s.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'Water'

# another (child) volume
mm = gam.g4_units('mm')
sheet = s.add_volume('Box', 'Sheet')
sheet.size = [40 * cm, 40 * cm, 1 * mm]
sheet.mother = 'Waterbox'
sheet.translation = [0 * cm, 0 * cm, -19 * cm]
sheet.material = 'Aluminium'

# Another one # FIXME

# default source for tests
source = s.add_source('TestProtonPy2', 'Default')
MeV = gam.g4_units('MeV')
source.energy = 150 * MeV
source.diameter = 2 * cm
source.n = 2000

# add stat actor
stats = s.add_actor('SimulationStatistics', 'Stats')

print(s.dump_sources())
print(s.dump_volumes(1))

# create G4 objects
s.initialize()

print(s.dump_sources())
print(s.dump_volumes(1))

# verbose
s.g4_com('/tracking/verbose 0')
# s.g4_com("/run/verbose 2")
# s.g4_com("/event/verbose 2")
# s.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.RUN)
s.start()

a = s.actors_info.Stats.g4_actor
print(a)

print()
print('Great, ALL done ! ')

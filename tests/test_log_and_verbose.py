#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from box import Box
import gam

# set log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()
sim.enable_g4_verbose(False)

# set random engine
sim.set_random_engine("MersenneTwister", 123456)

cm = gam.g4_units('cm')

# fake volume
#fake = sim.add_volume('Box', 'Fake')
#fake.size = [20 * cm, 20 * cm, 20 * cm]
#fake.translation = [0 * cm, 0 * cm, 15 * cm]
#fake.material = 'Air'

# add a simple volume
waterbox = sim.add_volume('Box', 'Waterbox')
waterbox.size = [20 * cm, 20 * cm, 20 * cm]
waterbox.translation = [0 * cm, 0 * cm, 15 * cm]
waterbox.material = 'Water'
#waterbox.mother = 'Fake'

# fake2 volume
#fake2 = sim.add_volume('Box', 'Fake2')
#fake2.size = [15 * cm, 15 * cm, 15 * cm]
#fake2.material = 'Water'
#fake2.mother = 'Waterbox'

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
source2.activity = 6.0 * Bq
source2.start_time = 0.55 * sec ## FIXME ???
source3 = sim.add_source('TestProtonPy2', 'source3')
source3.energy = 150 * MeV
source3.diameter = 20 * mm
source3.start_time = 0.6 * sec
source3.n = 5
source3.start_time = 0.25 * sec

# add stat actor
stats = sim.add_actor('SimulationStatistics', 'Stats')

dose = sim.add_actor('Dose3', 'Dose')
dose.attachedTo = 'Waterbox'

# run timing test #1
sec = gam.g4_units('second')
#sim.run_timing_intervals = [[0, 0.5 * sec]]
sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1.2 * sec]]  # one single run, start and stop at zero

# create G4 objects
sim.initialize()

# control log : INFO = each RUN, DEBUG = each Event
gam.source_log.setLevel(gam.EVENT)

# start simulation
sim.start()

stat = sim.actors_info.Stats
print(stat.g4_actor)
print('end.')

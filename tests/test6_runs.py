#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam

# set log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()
sim.enable_g4_verbose(False)

# set random engine
sim.set_random_engine("MersenneTwister", 123456)

cm = gam.g4_units('cm')

# add a simple volume
waterbox = sim.add_volume('Box', 'Waterbox')
waterbox.size = [20 * cm, 20 * cm, 20 * cm]
waterbox.translation = [0 * cm, 0 * cm, 15 * cm]
waterbox.material = 'Water'

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
source2.start_time = 0.55 * sec
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
sim.run_timing_intervals = [[0, 0.5 * sec],
                            [0.5 * sec, 1.2 * sec],
                            # Watch out : there is a 'hole' in the timeline
                            [1.5 * sec, 2.6 * sec],
                            ]

# create G4 objects
sim.initialize()

# control log : INFO = each RUN, DEBUG = each Event
gam.source_log.setLevel(gam.EVENT)

# start simulation
sim.start()

stat = sim.actors_info.Stats.g4_actor
print(stat)

assert stat.run_count == 3
assert stat.event_count == 31
assert stat.track_count == 362
assert stat.step_count == 1470

# FIXME better stat per run ?

gam.test_ok()

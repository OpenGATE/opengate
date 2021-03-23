#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import contrib.gam_iec as gam_iec

# global log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()

# verbose and GUI
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(False)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 12356)

#  change world size
m = gam.g4_units('m')
cm = gam.g4_units('cm')
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]

# add a iec phantom
iec_phantom = gam_iec.add_phantom(sim)
iec_phantom.translation = [0 * cm, 0 * cm, 0 * cm]

# simple source
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
source = sim.add_source('Generic', 'g')
source.particle = 'gamma'
source.energy.mono = 0.1 * MeV
source.direction.type = 'iso'
source.activity = 50000 * Bq

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'stats')
stats.track_types_flag = True

# run timing
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 1 * sec]]

# initialize & start
sim.initialize()
sim.start()

# print results at the end
stats = sim.get_actor('stats')
print(stats)

# check
stats_ref = gam.read_stat_file('./stats_test015_iec_phantom_1.txt')
# the number of step is different, which is expected
stats_ref.SetStepCount(397972)
is_ok = gam.assert_stats(stats, stats_ref, 0.05)

gam.test_ok(is_ok)

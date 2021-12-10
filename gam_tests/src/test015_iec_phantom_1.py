#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_iec_phantom as gam_iec
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# global log level
# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False

#  change world size
m = gam.g4_units('m')
cm = gam.g4_units('cm')
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]

# add a iec phantom
iec_phantom = gam_iec.add_phantom_old(sim)
iec_phantom.translation = [0 * cm, 3.5 * cm, 0 * cm]

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
stats.write(pathFile / '..' / 'output' / 'stats_test015_iec_phantom_1.txt')

# check
stats_ref = gam.SimulationStatisticsActor()
c = stats_ref.counts
c.run_count = 1
c.event_count = 49997
c.track_count = 53027
c.step_count = 468582
# stats_ref.pps = 2150
sec = gam.g4_units('second')
c.duration = c.event_count / 19441.5 * sec
print('-' * 80)
is_ok = gam.assert_stats(stats, stats_ref, 0.05)

gam.test_ok(is_ok)

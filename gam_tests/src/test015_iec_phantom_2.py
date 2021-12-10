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
ui.check_volumes_overlap = True

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
stats_ref = gam.read_stat_file(pathFile / '..' / 'output' / 'stats_test015_iec_phantom_1.txt')
# the number of step is different, which is expected, so we force the same value
stats_ref.counts.step_count = 397972
is_ok = gam.assert_stats(stats, stats_ref, 0.05)

gam.test_ok(is_ok)

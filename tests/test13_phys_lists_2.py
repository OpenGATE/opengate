#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from test13_phys_lists_base import create_pl_sim

# create simulation
sim = create_pl_sim()
sim.set_g4_random_engine("MersenneTwister", 1234)

# change physics
p = sim.physics_manager
p.name = 'QGSP_BERT_EMZ'
p.decay = True

# initialize
sim.initialize()

# start simulation
# sim.set_g4_verbose(True)
# sim.apply_g4_command("/tracking/verbose 1")
gam.source_log.setLevel(gam.DEBUG)  # FIXME do not work
sim.start()

stats = sim.get_actor('Stats')

# gate_test4_simulation_stats_actor
# Gate mac/main.mac
# stats_ref = gam.read_stat_file('./gate_test13_phys_lists/output/stat.txt')
stats_ref = gam.SimulationStatisticsActor('test')
stats_ref.SetRunCount(1)
stats_ref.SetEventCount(2061)
stats_ref.SetTrackCount(124734)
stats_ref.SetStepCount(531739)
sec = gam.g4_units('second')
stats_ref.fDuration = stats_ref.GetEventCount() / 511.3 * sec
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.05)

gam.test_ok(is_ok)

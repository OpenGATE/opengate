#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from test013_phys_lists_base import create_pl_sim

# create simulation
sim = create_pl_sim()

# remove ion sources
sim.source_manager.sources.pop('ion1')
sim.source_manager.sources.pop('ion2')

# change physics
p = sim.physics_manager
p.name = 'QGSP_BERT_EMZ'

# initialize
sim.initialize()

print('Phys list cuts:')
print(sim.physics_manager.dump_cuts())

# start simulation
# sim.set_g4_verbose(True)
# sim.apply_g4_command("/tracking/verbose 1")
gam.source_log.setLevel(gam.DEBUG)
sim.start()

stats = sim.get_actor('Stats')

# Gate mac/main_2.mac
stats_ref = gam.read_stat_file('./gate_test13_phys_lists/output/stat_2.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.05)

gam.test_ok(is_ok)

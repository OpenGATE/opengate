#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
from test013_phys_lists_base import create_pl_sim
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create simulation
sim = create_pl_sim()

# remove ion sources
sim.source_manager.user_info_sources.pop('ion1')
sim.source_manager.user_info_sources.pop('ion2')

# change physics
p = sim.get_physics_user_info()
p.physics_list_name = 'QGSP_BERT_EMZ'

# initialize
sim.initialize()

print('Phys list cuts:')
print(sim.physics_manager.dump_cuts())

# start simulation
# sim.set_g4_verbose(True)
# sim.apply_g4_command("/tracking/verbose 1")
sim.start()

stats = sim.get_actor('Stats')

# Gate mac/main_2.mac
stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'gate' / 'gate_test013_phys_lists' / 'output' / 'stat_2.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.1)

gam.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from test013_phys_lists_base import create_pl_sim

# create simulation
sim = create_pl_sim()
ui = sim.user_info
ui.g4_verbose = True

# remove ion sources
sim.source_manager.user_info_sources.pop('ion1')
sim.source_manager.user_info_sources.pop('ion2')

# change physics
p = sim.get_physics_user_info()
p.physics_list_name = 'G4EmStandardPhysics_option4'
p.enable_decay = False
cuts = p.production_cuts
um = gam.g4_units('um')
cuts.world.gamma = 7 * um
cuts.world.electron = 7 * um
cuts.world.positron = 7 * um
cuts.world.proton = 7 * um

# initialize
sim.initialize()

# print cuts
print('Phys list cuts:')
print(sim.physics_manager.dump_cuts())

# start simulation
# sim.apply_g4_command("/tracking/verbose 1")
gam.source_log.setLevel(gam.DEBUG)  # FIXME do not work
sim.start()

# Gate mac/main_1.mac
stats = sim.get_actor('Stats')
stats_ref = gam.read_stat_file('./gate_test13_phys_lists/output/stat_1.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.2)

gam.test_ok(is_ok)

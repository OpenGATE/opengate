#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
from test013_phys_lists_base import create_pl_sim
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create simulation
sim = create_pl_sim()

# keep only ion sources
sim.source_manager.user_info_sources.pop('gamma')

# change physics
p = sim.get_physics_user_info()
p.physics_list_name = 'G4EmStandardPhysics_option4'
p.enable_decay = True
p.apply_cuts = True  # default
cuts = p.production_cuts
mm = gam.g4_units('mm')
cuts.world.gamma = 1 * mm
cuts.world.electron = 0.1 * mm
cuts.world.positron = 1 * mm
cuts.world.proton = 1 * mm
cuts.b1.gamma = 1 * mm
cuts.b1.electron = 0.01 * mm
cuts.b1.positron = 1 * mm
cuts.b1.proton = 1 * mm

# initialize
sim.initialize()

print('Phys list cuts:')
print(sim.physics_manager.dump_cuts())

# start simulation
# sim.set_g4_verbose(True)
# sim.apply_g4_command("/tracking/verbose 1")
sim.start()

# Gate mac/main_3.mac
stats = sim.get_actor('Stats')
stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'gate' / 'gate_test013_phys_lists' / 'output' / 'stat_3.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.1)

gam.test_ok(is_ok)

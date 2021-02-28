#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from test13_phys_lists_base import create_pl_sim

# create simulation
sim = create_pl_sim()

# remove ion sources
sim.source_manager.sources.pop('ion1')
sim.source_manager.sources.pop('ion2')

# change physics
p = sim.physics_manager
p.name = 'G4EmStandardPhysics_option4'
p.decay = False
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
# sim.set_g4_verbose(True)
# sim.apply_g4_command("/tracking/verbose 1")
gam.source_log.setLevel(gam.DEBUG)  # FIXME do not work
sim.start()

# Gate mac/main_1.mac
stats = sim.get_actor('Stats')
stats_ref = gam.read_stat_file('./gate_test13_phys_lists/output/stat_1.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.2)

gam.test_ok(is_ok)

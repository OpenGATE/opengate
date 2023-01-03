#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from test013_phys_lists_helpers import create_pl_sim, phys_em_parameters

paths = gate.get_default_test_paths(__file__, "gate_test013_phys_lists")

# create simulation
sim = create_pl_sim()
ui = sim.user_info
ui.g4_verbose = True

# remove ion sources
sim.source_manager.user_info_sources.pop("ion1")
sim.source_manager.user_info_sources.pop("ion2")

# change physics
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option4"
p.enable_decay = True
p.apply_cuts = True  # default
cuts = p.production_cuts
um = gate.g4_units("um")
cuts.world.gamma = 7 * um
cuts.world.electron = 7 * um
cuts.world.positron = 7 * um
cuts.world.proton = 7 * um

# em parameters
# phys_em_parameters(p)

# print cuts
print("Phys list cuts:")
print(sim.physics_manager.dump_cuts())

# start simulation
# sim.apply_g4_command("/tracking/verbose 1")
output = sim.start()

# Gate mac/main_1.mac
stats = output.get_actor("Stats")
stats_ref = gate.read_stat_file(paths.gate_output / "stat_1.txt")
is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.1)

gate.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from test013_phys_lists_helpers import create_pl_sim, phys_em_parameters

paths = gate.get_default_test_paths(__file__, "gate_test013_phys_lists")

# create simulation
sim = create_pl_sim()

# remove ion sources
sim.source_manager.user_info_sources.pop("ion1")
sim.source_manager.user_info_sources.pop("ion2")

# change physics
p = sim.get_physics_user_info()
p.physics_list_name = "QGSP_BERT_EMZ"

# em parameters
phys_em_parameters(p)

print("Phys list cuts:")
print(sim.physics_manager.dump_cuts())

# start simulation
# sim.set_g4_verbose(True)
# sim.apply_g4_command("/tracking/verbose 1")
output = sim.start()

stats = output.get_actor("Stats")

# Gate mac/main_2.mac
stats_ref = gate.read_stat_file(paths.gate_output / "stat_2.txt")
is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.07)

gate.test_ok(is_ok)

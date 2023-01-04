#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from test013_phys_lists_helpers import create_pl_sim, phys_em_parameters

paths = gate.get_default_test_paths(__file__, "gate_test013_phys_lists")

# create simulation
sim = create_pl_sim()

# keep only ion sources
sim.source_manager.user_info_sources.pop("gamma")

# change physics
p = sim.get_physics_user_info()
p.physics_list_name = "QGSP_BERT_EMZ"
p.enable_decay = True
mm = gate.g4_units("mm")
cuts = p.production_cuts
cuts.world.gamma = 5 * mm
cuts.world.proton = 1 * mm
cuts.world.electron = -1  # default
cuts.world.positron = 3 * mm
cuts.waterbox.gamma = 2 * mm
cuts.b2.electron = 5 * mm

# em parameters
phys_em_parameters(p)

print("Phys list cuts:")
print(sim.physics_manager.dump_cuts())

# start simulation
# sim.set_g4_verbose(True)
# sim.apply_g4_command("/tracking/verbose 1")
output = sim.start()

stats = output.get_actor("Stats")

# gate_test4_simulation_stats_actor
# Gate mac/main_4.mac
f = paths.gate_output / "stat_5.txt"
print("Reference file", f)
stats_ref = gate.read_stat_file(f)
is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.13)

gate.test_ok(is_ok)

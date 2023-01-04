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
p.physics_list_name = "G4EmStandardPhysics_option4"
p.enable_decay = True
p.apply_cuts = True  # default
cuts = p.production_cuts
mm = gate.g4_units("mm")
cuts.world.gamma = 1 * mm
cuts.world.electron = 0.1 * mm
cuts.world.positron = 1 * mm
cuts.world.proton = 1 * mm
cuts.b1.gamma = 1 * mm
cuts.b1.electron = 0.01 * mm
cuts.b1.positron = 1 * mm
cuts.b1.proton = 1 * mm

# em parameters
phys_em_parameters(p)

print("Phys list cuts:")
print(sim.physics_manager.dump_cuts())

# start simulation
# sim.set_g4_verbose(True)
# sim.apply_g4_command("/tracking/verbose 1")
output = sim.start()

# Gate mac/main_3.mac
stats = output.get_actor("Stats")
stats_ref = gate.read_stat_file(paths.gate_output / "stat_3.txt")
is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.1)

gate.test_ok(is_ok)

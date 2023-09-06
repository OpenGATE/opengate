#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.user_hooks import check_production_cuts
from test013_phys_lists_helpers import create_pl_sim

paths = gate.get_default_test_paths(__file__, "gate_test013_phys_lists")

# create simulation
sim = create_pl_sim()

# keep only ion sources
sim.source_manager.user_info_sources.pop("gamma")

# change physics
sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
sim.physics_manager.enable_decay = True
mm = gate.g4_units("mm")

sim.physics_manager.global_production_cuts.gamma = 5 * mm
sim.physics_manager.global_production_cuts.electron = "default"
sim.physics_manager.global_production_cuts.positron = 3 * mm
sim.physics_manager.global_production_cuts.proton = 1 * mm

sim.physics_manager.set_production_cut(
    volume_name="waterbox",
    particle_name="gamma",
    value=2 * mm,
)
sim.physics_manager.set_production_cut(
    volume_name="b2",
    particle_name="electron",
    value=5 * mm,
)

# em parameters
sim.physics_manager.em_parameters.fluo = True
sim.physics_manager.em_parameters.auger = True
sim.physics_manager.em_parameters.auger_cascade = True
sim.physics_manager.em_parameters.pixe = True
sim.physics_manager.em_parameters.deexcitation_ignore_cut = True

sim.physics_manager.em_switches_world.deex = True
sim.physics_manager.em_switches_world.auger = True
sim.physics_manager.em_switches_world.pixe = True

print("Phys list cuts:")
print(sim.physics_manager.dump_production_cuts())

# start simulation
# sim.apply_g4_command("/tracking/verbose 1")
sim.user_info.g4_verbose = False
sim.user_fct_after_init = check_production_cuts
sim.run()

stats = sim.output.get_actor("Stats")

# gate_test4_simulation_stats_actor
# Gate mac/main_4.mac
f = paths.gate_output / "stat_5.txt"
print("Reference file", f)
stats_ref = gate.read_stat_file(f)
is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.13)

gate.test_ok(is_ok)

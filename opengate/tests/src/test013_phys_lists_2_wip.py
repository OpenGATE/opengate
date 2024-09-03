#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test013_phys_lists_helpers import create_pl_sim

paths = utility.get_default_test_paths(__file__, "gate_test013_phys_lists")

# create simulation
sim = create_pl_sim()

# remove ion sources
sim.source_manager.user_info_sources.pop("ion1")
sim.source_manager.user_info_sources.pop("ion2")

# change physics
sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"

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
# sim.set_g4_verbose(True)
# sim.g4_commands_after_init.append("/tracking/verbose 1")
sim.run()

stats = sim.get_actor("Stats")

# Gate mac/main_2.mac
stats_ref = utility.read_stat_file(paths.gate_output / "stat_2.txt")
is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.07)

utility.test_ok(is_ok)

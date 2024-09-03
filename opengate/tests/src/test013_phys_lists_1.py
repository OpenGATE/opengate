#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from test013_phys_lists_helpers import create_pl_sim

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test013_phys_lists")

    # create simulation via the helper function
    sim = create_pl_sim()
    sim.g4_verbose = True

    # remove ion sources
    sim.source_manager.user_info_sources.pop("ion1")
    sim.source_manager.user_info_sources.pop("ion2")

    # change physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    # enable decay via switch:
    # sim.physics_manager.enable_decay = True
    # or by activating the physics constructors:
    sim.physics_manager.special_physics_constructors.G4DecayPhysics = True
    sim.physics_manager.special_physics_constructors.G4RadioactiveDecayPhysics = True

    um = gate.g4_units.um
    global_cut = 7 * um
    sim.physics_manager.global_production_cuts.gamma = global_cut
    sim.physics_manager.global_production_cuts.electron = global_cut
    sim.physics_manager.global_production_cuts.positron = global_cut
    sim.physics_manager.global_production_cuts.proton = global_cut

    # print cuts
    print("Phys list cuts:")
    print(sim.physics_manager.dump_production_cuts())

    # start simulation
    # sim.g4_commands_after_init.append("/tracking/verbose 1")
    sim.run()

    # Gate mac/main_1.mac
    stats = sim.get_actor("Stats")
    stats_ref = utility.read_stat_file(paths.gate_output / "stat_1.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.12)

    utility.test_ok(is_ok)

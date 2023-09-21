#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.user_hooks import check_production_cuts
from test013_phys_lists_helpers import (
    create_pl_sim,
)

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "gate_test013_phys_lists")

    # create simulation
    sim = create_pl_sim()

    # keep only ion sources
    sim.source_manager.user_info_sources.pop("gamma")

    # change physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = True
    # cuts = p.production_cuts
    mm = gate.g4_units("mm")
    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 0.1 * mm
    sim.physics_manager.global_production_cuts.positron = 1 * mm
    sim.physics_manager.global_production_cuts.proton = 1 * mm

    reg = sim.add_region("reg")
    reg.production_cuts.gamma = 1 * mm
    reg.production_cuts.electron = 0.01 * mm
    reg.production_cuts.positron = 1 * mm
    reg.production_cuts.proton = 1 * mm
    reg.associate_volume("b1")

    # em parameters
    phys_em_parameters(p)

    print("Phys list cuts:")
    print(sim.physics_manager.dump_production_cuts())
    print("Volume tree:")
    print(sim.volume_manager.dump_tree_of_volumes())

    # start simulation
    sim.user_info.g4_verbose = False
    # sim.apply_g4_command("/tracking/verbose 1")
    sim.user_fct_after_init = check_production_cuts
    sim.run()

    # Gate mac/main_3.mac
    stats = sim.output.get_actor("Stats")
    stats_ref = gate.read_stat_file(paths.gate_output / "stat_3.txt")
    is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.1)

    gate.test_ok(is_ok)

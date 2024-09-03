#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from test013_phys_lists_helpers import create_pl_sim

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test013_phys_lists")

    # create simulation
    sim = create_pl_sim()

    # keep only ion sources
    sim.source_manager.user_info_sources.pop("gamma")

    # shortcut units
    mm = gate.g4_units.mm

    # change physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = True

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

    print("Phys list cuts:")
    print(sim.physics_manager.dump_production_cuts())

    # start simulation
    sim.g4_verbose = True
    # sim.g4_commands_after_init.append("/tracking/verbose 1")
    sim.run()

    stats = sim.get_actor("Stats")

    # gate_test4_simulation_stats_actor
    # Gate mac/main_4.mac
    f = paths.gate_output / "stat_4.txt"
    print("Reference file", f)
    stats_ref = utility.read_stat_file(f)
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.12)

    utility.test_ok(is_ok)

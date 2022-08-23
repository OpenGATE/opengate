#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from test013_phys_lists_base import create_pl_sim
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

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

# initialize
sim.initialize()

# print cuts
print("Phys list cuts:")
print(sim.physics_manager.dump_cuts())

# start simulation
# sim.apply_g4_command("/tracking/verbose 1")
sim.start()

# Gate mac/main_1.mac
stats = sim.get_actor("Stats")
stats_ref = gate.read_stat_file(
    pathFile
    / ".."
    / "data"
    / "gate"
    / "gate_test013_phys_lists"
    / "output"
    / "stat_1.txt"
)
is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.2)

gate.test_ok(is_ok)

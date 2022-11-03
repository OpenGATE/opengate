#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from test037_pet_hits_singles_base import *

paths = gate.get_default_test_paths(__file__, "gate_test037_pet")

# create the simulation
sim = gate.Simulation()
create_pet_simulation(sim, paths)

# timing
sec = gate.g4_units("second")
sim.run_timing_intervals = [[0, 0.00005 * sec]]

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# print results
stats = sim.get_actor("Stats")
print(stats)

# ----------------------------------------------------------------------------------------------------------

# check stats
print()
gate.warning(f"Check stats")
p = paths.gate / "output_test1"
stats_ref = gate.read_stat_file(p / "stats1.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.025)

# check root hits
hc = sim.get_actor_user_info("Hits")
f = p / "output1.root"
is_ok = check_root_hits(paths, 1, f, hc.output) and is_ok

# check root singles
sc = sim.get_actor_user_info("Singles")
is_ok = check_root_singles(paths, 1, f, sc.output) and is_ok

gate.test_ok(is_ok)

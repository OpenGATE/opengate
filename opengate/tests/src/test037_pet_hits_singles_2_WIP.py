#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from test037_pet_hits_singles_base import *

paths = gate.get_default_test_paths(__file__, "gate_test037_pet")

# create the simulation
sim = gate.Simulation()
create_pet_simulation(sim, paths, 2)

"""
NO visible change bw winner/centroid policies (on both legacy and current gate)
-> change geometry to enhance difference between both ?
"""

# change the digitizer adder policy
sc = sim.get_actor_user_info("Singles")
sc.policy = "EnergyWinnerPosition"
# sc.policy = "EnergyWeightedCentroidPosition"


p = sim.get_physics_user_info()
mm = gate.g4_units("mm")
sim.set_cut(f"pet_crystal", "all", 0.01 * mm)

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
# p = paths.gate / "output_test1"
p = paths.gate / "output"
stats_ref = gate.read_stat_file(p / "stats2.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.025)

# check root hits
hc = sim.get_actor_user_info("Hits")
is_ok = check_root_hits(paths, 2, hc.output) and is_ok

# check root singles
sc = sim.get_actor_user_info("Singles")
is_ok = check_root_singles(paths, 2, sc.output) and is_ok

gate.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test037_pet_hits_singles_base import *

paths = gate.get_default_test_paths(__file__, "gate_test037_pet")

v = "2_2"

# create the simulation
sim = gate.Simulation()
create_pet_simulation(sim, paths, v, "Singles_adder")


hc = sim.get_actor_user_info("Hits")

# change the digitizer adder
sc = sim.get_actor_user_info("Singles_adder")
sc.policy = "EnergyWeightedCentroidPosition"
# sc.output = None # do not save it
# gate.print_dic(sc)
import json

s = json.dumps(sc.__dict__, indent=2, default=str)
print(s)

# singles collection
module = sim.get_volume_user_info("pet_module")
die = sim.get_volume_user_info("pet_die")
sc = sim.add_actor("HitsAdderActor", "Singles")
sc.mother = module.name
sc.input_hits_collection = "Singles_adder"
# sc.policy = "EnergyWinnerPosition"
sc.policy = "EnergyWeightedCentroidPosition"
sc.output = hc.output
# gate.print_dic(sc)

# timing
sec = gate.g4_units("second")
sim.run_timing_intervals = [[0, 0.00003 * sec]]

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
stats_ref = gate.read_stat_file(p / f"stats{v}.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.025)

# check root hits
hc = sim.get_actor_user_info("Hits")
is_ok = check_root_hits(paths, "output", v, hc.output) and is_ok

# check root singles
sc = sim.get_actor_user_info("Singles")
is_ok = check_root_singles(paths, "output", v, sc.output) and is_ok

gate.test_ok(is_ok)

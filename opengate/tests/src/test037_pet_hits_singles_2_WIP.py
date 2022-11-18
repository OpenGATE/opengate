#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test037_pet_hits_singles_base import *

paths = gate.get_default_test_paths(__file__, "gate_test037_pet")

# test version
v = "2_2"

# create the simulation
sim = gate.Simulation()
crystal = create_pet_simulation(sim, paths)
module = sim.get_volume_user_info("pet_module")

# digitizer hits
hc = sim.add_actor("HitsCollectionActor", "Hits")
hc.mother = crystal.name
hc.output = paths.output / f"test037_test{v}.root"
hc.attributes = [
    "PostPosition",
    "TotalEnergyDeposit",
    "PreStepUniqueVolumeID",
    "GlobalTime",
]

# digitizer singles in two steps
# Step 1: group all the hits per volume
gc = sim.add_actor("HitsAdderActor", "GroupedHits")
gc.mother = module.name  # group by module
gc.input_hits_collection = "Hits"
gc.policy = "EnergyWeightedCentroidPosition"

# Step 2: discretize the position
sc = sim.add_actor("HitsDiscretizerActor", "Singles")
sc.mother = module.name
sc.input_hits_collection = "GroupedHits"
sc.discrete_position_volume = [crystal.name, crystal.name, crystal.name]

sc = sim.add_actor("HitsDiscretizerActor", "Singles2")
sc.mother = module.name
sc.input_hits_collection = "GroupedHits"
sc.discrete_position_volume = [crystal.name, crystal.name, False]

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
# p = paths.gate / "output_test1"
p = paths.gate / "output"
stats_ref = gate.read_stat_file(p / f"stats{v}.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.025)

# check root hits
hc = sim.get_actor_user_info("Hits")
f = p / f"output{v}.root"
is_ok = check_root_hits(paths, v, f, hc.output) and is_ok

# check root singles
sc = sim.get_actor_user_info("Singles2")
is_ok = check_root_singles(paths, v, f, sc.output) and is_ok

gate.test_ok(is_ok)

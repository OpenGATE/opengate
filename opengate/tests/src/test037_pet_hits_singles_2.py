#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test037_pet_hits_singles_helpers import *

paths = gate.get_default_test_paths(__file__, "gate_test037_pet")

# test version
v = "2_2"

# create the simulation
sim = gate.Simulation()
crystal = create_pet_simulation(sim, paths)
module = sim.get_volume_user_info("pet_module")
die = sim.get_volume_user_info("pet_die")
stack = sim.get_volume_user_info("pet_stack")

# digitizer hits
hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
hc.mother = crystal.name
hc.output = paths.output / f"test037_test{v}.root"
hc.attributes = [
    "PostPosition",
    "TotalEnergyDeposit",
    "PreStepUniqueVolumeID",
    "GlobalTime",
]

# Readout (not need for adder)
sc = sim.add_actor("DigitizerReadoutActor", "Singles2_1")
sc.output = paths.output / f"test037_test{v}.root"
sc.input_digi_collection = "Hits"
sc.group_volume = stack.name  # should be depth=1 in Gate
sc.discretize_volume = crystal.name
sc.policy = "EnergyWeightedCentroidPosition"

# Readout: another one, with different option (in the same output file)
sc = sim.add_actor("DigitizerReadoutActor", "Singles2_2")
sc.output = paths.output / f"test037_test{v}.root"
sc.input_digi_collection = "Hits"
sc.group_volume = crystal.name  # should be depth=4 in Gate
sc.discretize_volume = crystal.name
sc.policy = "EnergyWeightedCentroidPosition"

# timing
sec = gate.g4_units("second")
sim.run_timing_intervals = [[0, 0.00005 * sec]]

# start simulation
output = sim.start()

# print results
stats = output.get_actor("Stats")
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
hc = output.get_actor("Hits").user_info
f = p / f"output{v}.root"
is_ok = check_root_hits(paths, v, f, hc.output) and is_ok

# check root singles
sc = output.get_actor("Singles2_1").user_info
f = p / f"output2_1.root"
is_ok = check_root_singles(paths, "2_1", f, sc.output, sc.name) and is_ok

# check root singles
sc = output.get_actor("Singles2_2").user_info
f = p / f"output2_2.root"
is_ok = check_root_singles(paths, "2_2", f, sc.output, sc.name) and is_ok

gate.test_ok(is_ok)

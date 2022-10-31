#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.pet_philips_vereos as pet_vereos
import opengate.contrib.phantom_necr as phantom_necr

paths = gate.get_default_test_paths(__file__, "gate_test037_pet")

"""
Simulation of a PET VEREOS with NEMA NECR phantom.
- phantom is a simple cylinder and linear source
- output is hits and singles only (no coincidences)
- also digitizer is simplified: only raw hits and adder (for singles)
"""

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.check_volumes_overlap = False

# units
m = gate.g4_units("m")
mm = gate.g4_units("mm")
cm = gate.g4_units("cm")
Bq = gate.g4_units("Bq")
MBq = Bq * 1e6
sec = gate.g4_units("second")

#  change world size
world = sim.world
world.size = [3 * m, 3 * m, 3 * m]
world.material = "G4_AIR"

# add a PET VEREOS
pet = pet_vereos.add_pet(sim, "pet")

# add table
bed = pet_vereos.add_table(sim, "pet")

# add NECR phantom
phantom = phantom_necr.add_necr_phantom(sim, "phantom")

# physics
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option4"
sim.set_cut("world", "all", 1 * m)
sim.set_cut(phantom.name, "all", 0.1 * mm)
sim.set_cut(bed.name, "all", 0.1 * mm)
sim.set_cut(f"{pet.name}_crystal", "all", 0.1 * mm)

# default source for tests
source = phantom_necr.add_necr_source(sim, phantom)
total_yield = gate.get_rad_yield("F18")
print("Yield for F18 (nb of e+ per decay) : ", total_yield)
source.activity = 3000 * Bq * total_yield
source.activity = 1787.914158 * MBq * total_yield
source.half_life = 6586.26 * sec
source.energy.type = "F18_analytic"  # WARNING not ok, but similar to previous Gate
# source.energy.type = "F18"  # this is the correct F18 e+ source

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "Stats")
s.track_types_flag = True

# hits collection
hc = sim.add_actor("HitsCollectionActor", "Hits")
# get crystal volume by looking for the word crystal in the name
l = sim.get_all_volumes_user_info()
crystal = l[[k for k in l if "crystal" in k][0]]
hc.mother = crystal.name
print("Crystal :", crystal.name)
hc.output = paths.output / "test037_test1.root"
hc.attributes = [
    "PostPosition",
    "TotalEnergyDeposit",
    "TrackVolumeCopyNo",
    "PreStepUniqueVolumeID",
    "PostStepUniqueVolumeID",
    "GlobalTime",
    # "KineticEnergy", # not needed
    # "ProcessDefinedStep", # not needed
]

# singles collection
sc = sim.add_actor("HitsAdderActor", "Singles")
sc.mother = crystal.name
sc.input_hits_collection = "Hits"
# sc.policy = "EnergyWinnerPosition"
sc.policy = "EnergyWeightedCentroidPosition"
# the following attributes is not needed in singles
# sc.skip_attributes = ["KineticEnergy"]
sc.output = hc.output

# timing
sim.run_timing_intervals = [[0, 0.0002 * sec]]

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

# check phsp (hits)
print()
gate.warning(f"Check root")
ref_file = p / "output1.root"
hc_file = hc.output
checked_keys = [
    "PostPosition_X",
    "PostPosition_Y",
    "PostPosition_Z",
    "TotalEnergyDeposit",
    "GlobalTime",
]
checked_keys_ref = ["posX", "posY", "posZ", "edep", "time"]
scalings_ref = [1.0] * len(checked_keys)
scalings = [1.0] * len(checked_keys)
scalings[checked_keys.index("GlobalTime")] = 1e-9  # time in ns
tols = [1.0] * len(checked_keys)
tols[checked_keys_ref.index("posX")] = 3
tols[checked_keys_ref.index("posY")] = 3.5
tols[checked_keys_ref.index("posZ")] = 0.5
tols[checked_keys_ref.index("edep")] = 0.005
tols[checked_keys_ref.index("time")] = 0.0001

is_ok = (
    gate.compare_root3(
        ref_file,
        hc_file,
        "Hits",
        "Hits",
        checked_keys_ref,
        checked_keys,
        tols,
        scalings_ref,
        scalings,
        paths.output / "test037_test1_hits.png",
    )
    and is_ok
)

# check phsp (singles)
print()
gate.warning(f"Check root")
checked_keys_ref = ["globalPosX", "globalPosY", "globalPosZ", "energy", "time"]
tols[checked_keys_ref.index("energy")] = 0.02
is_ok = (
    gate.compare_root3(
        ref_file,
        hc_file,
        "Singles",
        "Singles",
        checked_keys_ref,
        checked_keys,
        tols,
        scalings_ref,
        scalings,
        paths.output / "test037_test1_singles.png",
    )
    and is_ok
)


gate.test_ok(is_ok)

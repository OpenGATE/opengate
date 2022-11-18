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
ui.g4_verbose = True
ui.g4_verbose_level = 2
# ui.number_of_threads = 2
# ui.force_multithread_mode = True

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
sim.add_material_database(paths.gate_data / "GateMaterials_pet.db")
pet = pet_vereos.add_pet_debug(sim, "pet", create_housing=False, create_mat=False)

# add table
# bed = pet_vereos.add_table(sim, "pet")

# add NECR phantom
# phantom = phantom_necr.add_necr_phantom(sim, "phantom")

# physics
p = sim.get_physics_user_info()
# p.enable_decay = True #not needed (?)
p.physics_list_name = "G4EmStandardPhysics_option4"
sim.set_cut("world", "all", 1 * m)
sim.set_cut(f"{pet.name}_crystal", "all", 1 * mm)

# em = p.g4_em_parameters
# print('em', em)
import opengate_core as g4

em = g4.G4EmParameters.Instance()
print("em", em)
em.SetFluo(True)
em.SetAuger(True)
em.SetAugerCascade(True)
em.SetPixe(True)
em.SetApplyCuts(True)

print("em pix", em.Pixe())
print("em fluo", em.Fluo())
print("em Auger", em.Auger())
print("em AugerCascade", em.AugerCascade())
print("em ApplyCuts", em.ApplyCuts())
print("em min E", em.MinKinEnergy())
print("em max E", em.MaxKinEnergy())

# emPar->SetMinEnergy(mEmin); ???


# default source for tests
source = phantom_necr.add_necr_source_debug(sim, "mysource")
total_yield = gate.get_rad_yield("F18")
print("Yield for F18 (nb of e+ per decay) : ", total_yield)
source.activity = 1787.914158 * MBq * total_yield
source.half_life = 6586.26 * sec
# source.energy.type = "F18_analytic"  # WARNING not ok, but similar to previous Gate
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
hc.output = paths.output / "test037_test0.root"
hc.attributes = [
    "PostPosition",
    "TotalEnergyDeposit",
    "TrackVolumeCopyNo",
    "PreStepUniqueVolumeID",
    "PreStepUniqueVolumeID",
    "GlobalTime",
    # "KineticEnergy", # not needed
    # "ProcessDefinedStep", # not needed
]
hc.keep_zero_edep = False  # 'False' is the default
hc.debug = False

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
sim.run_timing_intervals = [[0, 0.0001 * sec]]
if ui.visu:
    sim.run_timing_intervals = [[0, 0.00000002 * sec]]

eV = gate.g4_units("eV")
GeV = gate.g4_units("GeV")

# pct = g4.G4ProductionCutsTable.GetProductionCutsTable()
# pct.SetEnergyRange(250 * eV, 0.5 * GeV) ## do nothing :(

# create G4 objects
sim.initialize()
# sim.check_volumes_overlap(True)

em = g4.G4EmParameters.Instance()
em.SetFluo(True)
em.SetAuger(True)
em.SetAugerCascade(True)
em.SetPixe(True)
em.SetApplyCuts(True)
print("2 em", em)
print("em pix", em.Pixe())
print("em fluo", em.Fluo())
print("em Auger", em.Auger())
print("em AugerCascade", em.AugerCascade())
print("em fluo", em.ApplyCuts())
print("em min E", em.MinKinEnergy())
print("em max E", em.MaxKinEnergy())

# em.SetMinEnergy(250 * eV)
# print('em min E', em.MinKinEnergy())
# print('em max E', em.MaxKinEnergy())
# p.enable_decay = True #not needed (?)

# pct = g4.G4ProductionCutsTable.GetProductionCutsTable()
# pct.SetEnergyRange(250 * eV, 0.5 * GeV)

# sim.set_cut("world", "all", 1 * m)

vm = sim.volume_manager
t = vm.dump_defined_material(10)
print(t)
# exit(0)

m = vm.find_or_build_material("LYSO_debug")
print(m)
# exit(0)

# start simulation
sim.start()

em = g4.G4EmParameters.Instance()
print("3em", em)
print("em pix", em.Pixe())
print("em fluo", em.Fluo())
print("em Auger", em.Auger())
print("em AugerCascade", em.AugerCascade())
print("em fluo", em.ApplyCuts())

# print results
stats = sim.get_actor("Stats")
print(stats)

# ----------------------------------------------------------------------------------------------------------

# check stats
print()
gate.warning(f"Check stats")
p = paths.gate / "output"
stats_ref = gate.read_stat_file(p / "stats0.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.025)

print()
gate.warning(f"Check stats")
p = paths.gate / "output_test1"
stats_ref = gate.read_stat_file(p / "stats1.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.025)

# check phsp (new version)
p = paths.gate / "output"
k1 = ["posX", "posY", "posZ", "edep", "time"]
k2 = [
    "PostPosition_X",
    "PostPosition_Y",
    "PostPosition_Z",
    "TotalEnergyDeposit",
    "GlobalTime",
]
p1 = gate.root_compare_param_tree(p / "output0.root", "Hits", k1)
p2 = gate.root_compare_param_tree(hc.output, "Hits", k2)
p2.scaling[p2.the_keys.index("GlobalTime")] = 1e-9  # time in ns
p = gate.root_compare_param(p1.the_keys, paths.output / "test037_test0_hits.png")
p.tols[k1.index("posX")] = 3
p.tols[k1.index("posY")] = 3.5
p.tols[k1.index("posZ")] = 0.5
p.tols[k1.index("edep")] = 0.002
p.tols[k1.index("time")] = 0.0001
is_ok = gate.root_compare4(p1, p2, p) and is_ok

print()
print()
print()

# check phsp (hits)
print()
gate.warning(f"Check root")
p = paths.gate / "output"
ref_file = p / "output0.root"
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
tols[checked_keys_ref.index("edep")] = 0.002
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
        paths.output / "test037_test0_hits.png",
        nb_bins=300,
    )
    and is_ok
)

print()
import uproot

hits1 = uproot.open(ref_file)["Hits"].arrays(library="numpy")
hits2 = uproot.open(hc_file)["Hits"].arrays(library="numpy")
edep1 = hits1["edep"]
edep2 = hits2["TotalEnergyDeposit"]
print(edep1.shape, edep2.shape)
epsilon = 0
a1 = edep1[edep1 <= epsilon]
a2 = edep2[edep2 <= epsilon]
print(a1, a1.shape)
print(a2, a2.shape)
print(f"Nb of zero in edep1 {len(a1)}")
print(f"Nb of zero in edep2 {len(a2)}")

print()

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
        paths.output / "test037_test0_singles.png",
    )
    and is_ok
)

gate.test_ok(is_ok)

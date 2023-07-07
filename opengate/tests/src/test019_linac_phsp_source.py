#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
import gatetools.phsp as phsp
import matplotlib.pyplot as plt
import os
import subprocess

paths = gate.get_default_test_paths(
    __file__, "gate_test019_linac_phsp", output_folder="test019"
)

# This test need the output of test019_linac_phsp.py
# If the output of test019_linac_phsp.py does not exist (eg: random test), create it
if not os.path.isfile(paths.output / "test019_hits.root"):
    print("---------- Begin of test019_linac_phsp.py ----------")
    subprocess.call(["python", paths.current / "test019_linac_phsp.py"])
    print("----------- End of test019_linac_phsp.py -----------")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
# ui.visu = True
ui.visu_type = "vrml"
ui.check_volumes_overlap = False
# ui.running_verbose_level = gate.EVENT
ui.number_of_threads = 1
ui.random_seed = "auto"

# units
m = gate.g4_units("m")
mm = gate.g4_units("mm")
cm = gate.g4_units("cm")
nm = gate.g4_units("nm")
Bq = gate.g4_units("Bq")
MeV = gate.g4_units("MeV")

#  adapt world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# virtual plane for phase space
plane = sim.add_volume("Tubs", "phase_space_plane")
plane.material = "G4_AIR"
plane.rmin = 0
plane.rmax = 70 * mm
plane.dz = 1 * nm  # half height
plane.rotation = Rotation.from_euler("xy", [180, 30], degrees=True).as_matrix()
plane.translation = [-5 * mm, 20 * mm, 33 * mm]
plane.color = [1, 0, 0, 1]  # red

plane2 = sim.add_volume("Tubs", "phase_space_plane2")
plane2.material = "G4_AIR"
plane2.rmin = 0
plane2.rmax = 70 * mm
plane2.dz = 1 * nm  # half height
plane2.translation = [0 * mm, 0 * mm, -300.001 * mm]
plane2.color = [1, 0, 0, 1]  # red

# phsp source
source = sim.add_source("PhaseSpaceSource", "phsp_source_local")
source.mother = plane.name
source.phsp_file = paths.output / "test019_hits.root"
source.position_key = "PrePositionLocal"
source.direction_key = "PreDirectionLocal"
source.global_flag = False
source.particle = "gamma"
source.batch_size = 4000
source.n = 20000 / ui.number_of_threads

# phsp source
source = sim.add_source("PhaseSpaceSource", "phsp_source_global")
source.mother = world.name
source.phsp_file = paths.output / "test019_hits.root"
source.position_key = "PrePosition"
source.direction_key = "PreDirection"
source.global_flag = True
source.particle = "gamma"
source.batch_size = 3000
source.n = 20000 / ui.number_of_threads

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "Stats")
s.track_types_flag = True

# PhaseSpace Actor
ta1 = sim.add_actor("PhaseSpaceActor", "PhaseSpace1")
ta1.mother = plane.name
ta1.attributes = [
    "KineticEnergy",
    "Weight",
    "PostPosition",
    "PrePosition",
    "PrePositionLocal",
    "ParticleName",
    "PreDirection",
    "PreDirectionLocal",
    "PostDirection",
    "TimeFromBeginOfEvent",
    "GlobalTime",
    "LocalTime",
    "EventPosition",
]
ta1.output = paths.output / "test019_hits_phsp_source_local.root"
ta1.debug = False
f = sim.add_filter("ParticleFilter", "f")
f.particle = "gamma"
ta1.filters.append(f)

# PhaseSpace Actor
ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace2")
ta2.mother = plane2.name
ta2.attributes = [
    "KineticEnergy",
    "Weight",
    "PostPosition",
    "PrePosition",
    "PrePositionLocal",
    "ParticleName",
    "PreDirection",
    "PreDirectionLocal",
    "PostDirection",
    "TimeFromBeginOfEvent",
    "GlobalTime",
    "LocalTime",
    "EventPosition",
]
ta2.output = paths.output / "test019_hits_phsp_source_global.root"
ta2.debug = False
f = sim.add_filter("ParticleFilter", "f")
f.particle = "gamma"
ta2.filters.append(f)

# phys
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option4"
p.enable_decay = False
sim.physics_manager.global_production_cuts.gamma = 1 * mm
sim.physics_manager.global_production_cuts.electron = 1 * mm
sim.physics_manager.global_production_cuts.positron = 1 * mm

# start simulation
output = sim.start()

# print results
stats = output.get_actor("Stats")
print(stats)

# print source phsp info
s1 = output.get_source("phsp_source_local").particle_generator
print(f"Source local :  {s1.num_entries} elements, {s1.cycle_count} cycle")
s2 = output.get_source("phsp_source_global").particle_generator
print(f"Source global : {s2.num_entries} elements, {s2.cycle_count} cycle")

# --------------------------------------------------------------
# Test LOCAL position
print()
print("Test GLOBAL position")
fn1 = paths.output / "test019_hits.root"
fn2 = ta1.output
print("Reference gate tree : ", fn1)
print("Checked Tree : ", fn2)
data_ref, keys_ref, _ = phsp.load(fn1)
data, keys, _ = phsp.load(fn2, "PhaseSpace1")

keys1 = [
    "PrePositionLocal_X",
    "PrePositionLocal_Y",
    "PrePositionLocal_Z",
    "KineticEnergy",
    "Weight",
]
keys2 = keys1
tols = [0.3] * len(keys1)
scalings = [1.0] * len(keys1)
is_ok = gate.compare_trees(
    data_ref, keys_ref, data, keys, keys1, keys2, tols, scalings, scalings, True
)

# figure
plt.suptitle(f"Values: {len(data_ref)} vs {len(data)}")
# plt.show()
fn = paths.output / "test019_source_local.png"
plt.savefig(fn)
print(f"Figure in {fn}")

# --------------------------------------------------------------
# Test GLOBAL position
print()
print("Test GLOBAL position")
fn1 = paths.output / "test019_hits.root"
fn2 = ta2.output
print("Reference gate tree : ", fn1)
print("Checked Tree : ", fn2)
data_ref, keys_ref, _ = phsp.load(fn1)
data, keys, _ = phsp.load(fn2, "PhaseSpace2")

keys1 = ["PrePosition_X", "PrePosition_Y", "PrePosition_Z", "KineticEnergy", "Weight"]
keys2 = keys1
tols = [0.3] * len(keys1)
scalings = [1.0] * len(keys1)
is_ok = (
    gate.compare_trees(
        data_ref, keys_ref, data, keys, keys1, keys2, tols, scalings, scalings, True
    )
    and is_ok
)

# figure
plt.suptitle(f"Values: {len(data_ref)} vs {len(data)}")
# plt.show()
fn = paths.output / "test019_source_global.png"
plt.savefig(fn)
print(f"Figure in {fn}")

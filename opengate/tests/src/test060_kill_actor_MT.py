#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import uproot
import opengate as gate
import pathlib
from scipy.spatial.transform import Rotation
import gatetools.phsp as phsp
import matplotlib.pyplot as plt
import numpy as np
import itk


current_path = pathlib.Path(__file__).parent.resolve()
output_path = current_path / ".." / "output"

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
# ui.visu_type = "vrml"
ui.check_volumes_overlap = False
# ui.running_verbose_level = gate.EVENT
ui.number_of_threads = 8
ui.random_seed = "auto"

# units
m = gate.g4_units("m")
km = gate.g4_units("km")
mm = gate.g4_units("mm")
cm = gate.g4_units("cm")
nm = gate.g4_units("nm")
Bq = gate.g4_units("Bq")
MeV = gate.g4_units("MeV")
keV = gate.g4_units("keV")
gcm3 = gate.g4_units("g/cm3")

#  adapt world size
world = sim.world
world.size = [2 * m, 2 * m, 65 * cm]

# kill actor volume block


kill_P = sim.add_volume("Box", "Kill_plane")
kill_P.mother = world.name
kill_P.material = "G4_AIR"
kill_P.size = [1 * m, 1 * m, 1 * nm]
kill_P.translation = [0 * mm, 0 * mm, -2 * nm]
kill_P.color = [0, 1, 0, 1]


# source

nb_part_1 = 1000 / ui.number_of_threads
mean_E = 1 * MeV
source = sim.add_source("GenericSource", "photon_source")
source.particle = "gamma"
source.n = nb_part_1
source.position.type = "box"
source.position.size = [0 * cm, 0 * cm, 0 * cm]
source.direction.type = "momentum"
source.mother = world.name
source.direction.momentum = [0, 0, -1]
source.energy.type = "mono"
source.energy.mono = mean_E

# source_2
nb_part_2 = ui.number_of_threads / ui.number_of_threads
source = sim.add_source("GenericSource", "photon_source_2")
source.particle = "gamma"
source.n = nb_part_2
source.position.type = "box"
source.position.size = [0 * cm, 0 * cm, 0 * cm]
source.position.translation = [0 * cm, 0 * cm, -30 * cm]
source.direction.type = "momentum"
source.mother = world.name
source.direction.momentum = [0, 0, 1]
source.energy.type = "mono"
source.energy.mono = mean_E


s = sim.add_actor("SimulationStatisticsActor", "Stats")
# s.track_types_flag = True

# add phase space plan

phsp = sim.add_volume("Box", "phase_space_plane")
phsp.mother = world.name
phsp.material = "G4_AIR"
phsp.size = [1 * m, 1 * m, 1 * nm]
phsp.translation = [0 * m, 0 * m, -20 * cm]
phsp.color = [1, 0, 0, 1]  # red


# PhaseSpace Actor
Phsp_act = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
Phsp_act.mother = phsp.name
Phsp_act.attributes = [
    "EventID",
]
Phsp_act.output = output_path / "test060.root"
Phsp_act.debug = False


# Kill Actor to add


Kill_act = sim.add_actor("KillActor", "KillAct")
Kill_act.mother = kill_P.name
Kill_act.kill = True

# Physic list and cuts
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option3"
p.enable_decay = False
sim.physics_manager.global_production_cuts.gamma = 1 * mm
sim.physics_manager.global_production_cuts.electron = 1 * mm
sim.physics_manager.global_production_cuts.positron = 1 * mm


output = sim.start()

# print results
stats = output.get_actor("Stats")
h = output.get_actor("PhaseSpace")
print(stats)

f_phsp = uproot.open(output_path / "test060.root")
arr = f_phsp["PhaseSpace"].arrays()
print("Number of detected events :", len(arr))
print("Number of expected events :", ui.number_of_threads)
# EventID = arr[0]

is_ok = len(arr) == ui.number_of_threads
gate.test_ok(is_ok)

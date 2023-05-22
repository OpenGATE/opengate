#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate

paths = gate.get_default_test_paths(__file__, "gate_test019_linac_phsp")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = True
ui.check_volumes_overlap = False
ui.running_verbose_level = gate.EVENT
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
plane.mother = world.name
plane.material = "G4_AIR"
plane.rmin = 0
plane.rmax = 70 * mm
plane.dz = 1 * nm  # half height
plane.translation = [0, 0, -300.1 * mm]
plane.color = [1, 0, 0, 1]  # red

# phsp source
source = sim.add_source("PhaseSpaceSource", "phsp_source")
source.mother = plane.name
source.phsp_file = paths.output / "test019_hits.root"
source.particle = "gamma"
source.batch_size = 100
source.global_flag = True
source.n = 500 / ui.number_of_threads

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "Stats")
s.track_types_flag = True

# PhaseSpace Actor
ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
ta2.mother = plane.name
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
ta2.output = paths.output / "test019_hits_phsp_source.root"
ta2.debug = False
f = sim.add_filter("ParticleFilter", "f")
f.particle = "gamma"
ta2.filters.append(f)

# phys
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option4"
p.enable_decay = False
cuts = p.production_cuts
cuts.world.gamma = 1 * mm
cuts.world.electron = 1 * mm
cuts.world.positron = 1 * mm

# start simulation
output = sim.start()

# print results
stats = output.get_actor("Stats")
print(stats)

h = output.get_actor("PhaseSpace")
print(h)

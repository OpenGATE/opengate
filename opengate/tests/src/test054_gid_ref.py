#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from test053_gamma_from_ion_decay_helpers import *

paths = gate.get_default_test_paths(__file__, "")

sim = gate.Simulation()

# units
nm = gate.g4_units("nm")
m = gate.g4_units("m")
mm = gate.g4_units("mm")
km = gate.g4_units("km")
cm = gate.g4_units("cm")
Bq = gate.g4_units("Bq")

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.number_of_threads = 1
ui.visu = False
ui.random_seed = "auto"

# activity
sec = gate.g4_units("second")
duration = 100 * sec
activity = 1000 * Bq / ui.number_of_threads
if ui.visu:
    activity = 1 * Bq

# world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]
world.material = "G4_WATER"

# physics
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option4"
p.enable_decay = True
sim.set_cut("world", "all", 1e6 * mm)

# sources
# ui.running_verbose_level = gate.EVENT
s1 = sim.add_source("GenericSource", "ac225")
s1.particle = "ion 89 225"  # Ac225
# s1.particle = "ion 83 213"  # Bi213
s1.position.type = "sphere"
s1.position.radius = 1 * nm
s1.position.translation = [0, 0, 0]
s1.direction.type = "iso"
s1.activity = activity

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "stats")
s.track_types_flag = True
s.output = paths.output / "test054_stats_ref_ion_source.txt"

# phsp actor
phsp = sim.add_actor("PhaseSpaceActor", "phsp")
phsp.attributes = ["KineticEnergy", "GlobalTime"]
phsp.output = paths.output / "test054_ref_ion_source.root"

f = sim.add_filter("ParticleFilter", "f1")
f.particle = "gamma"
phsp.filters.append(f)

f = sim.add_filter("TrackCreatorProcessFilter", "f2")
f.process_name = "RadioactiveDecay"
phsp.filters.append(f)

# go
# ui.running_verbose_level = gate.EVENT
# sim.apply_g4_command("/tracking/verbose 2")
sim.run_timing_intervals = [[0, duration]]
output = sim.start()

# print stats
stats = output.get_actor("stats")
print(stats)

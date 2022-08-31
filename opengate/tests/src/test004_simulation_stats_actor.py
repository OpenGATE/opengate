#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import pathlib

paths = gate.get_default_test_paths(__file__, "gate_test004_simulation_stats_actor")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = "MersenneTwister"

# set the world size like in the Gate macro
m = gate.g4_units("m")
world = sim.world
world.size = [3 * m, 3 * m, 3 * m]

# add a simple waterbox volume
waterbox = sim.add_volume("Box", "Waterbox")
cm = gate.g4_units("cm")
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = "G4_WATER"

# default source for tests
keV = gate.g4_units("keV")
mm = gate.g4_units("mm")
Bq = gate.g4_units("Bq")
source = sim.add_source("Generic", "Default")
source.particle = "gamma"
source.energy.mono = 80 * keV
source.direction.type = "momentum"
source.direction.momentum = [0, 0, 1]
source.activity = 200000 * Bq

# add stat actor
sim.add_actor("SimulationStatisticsActor", "Stats")

# print before init
print(sim)
print("-" * 80)
print(sim.dump_volumes())
print(sim.dump_sources())
print(sim.dump_actors())
print("-" * 80)
print("Volume types :", sim.dump_volume_types())
print("Source types :", sim.dump_source_types())
print("Actor types  :", sim.dump_actor_types())

# create G4 objects
sim.initialize()

# print after init
print(sim)
print("Simulation seed:", sim.actual_random_seed)

# verbose
# sim.g4_apply_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
sim.start()
print(sim.dump_sources())

stats = sim.get_actor("Stats")
print(stats)

# gate_test4_simulation_stats_actor
# Gate mac/main.mac
stats_ref = gate.read_stat_file(paths.gate / "output" / "stat.txt")
print("-" * 80)
is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.03)

gate.test_ok(is_ok)

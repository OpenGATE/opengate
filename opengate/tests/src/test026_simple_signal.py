#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = "MersenneTwister"
ui.random_seed = "auto"

print(ui)

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
stats = sim.add_actor("SimulationStatisticsActor", "Stats")
stats.track_types_flag = True

# create G4 objects
sim.initialize()

# start simulation
# sim.apply_g4_command("/run/verbose 1")
sim.start()

# get result
stats = sim.get_actor("Stats")

# gate_test4_simulation_stats_actor
# Gate mac/main.mac
stats_ref = gate.read_stat_file(
    pathFile
    / ".."
    / "data"
    / "gate"
    / "gate_test004_simulation_stats_actor"
    / "output"
    / "stat.txt"
)
is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.03)

gate.test_ok(is_ok)

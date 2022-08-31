#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate

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
sim.add_actor("TestActor", "Stats2")

# create G4 objects
sim.initialize()

# start simulation
sim.start()

stats = sim.get_actor("Stats")
print(stats)
print("-" * 50)

stats = sim.get_actor("Stats2")
print(stats)

# FIXME todo
gate.test_ok(False)

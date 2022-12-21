#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import pathlib
import os
import threading
import copy
from multiprocessing import Process

pathFile = pathlib.Path(__file__).parent.resolve()

m = gate.g4_units("m")
cm = gate.g4_units("cm")
keV = gate.g4_units("keV")
mm = gate.g4_units("mm")
Bq = gate.g4_units("Bq")

sim = gate.Simulation()

ui = sim.user_info
ui.verbose_level = gate.DEBUG
ui.running_verbose_level = gate.RUN
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = "MersenneTwister"
ui.random_seed = "auto"
# ui.number_of_threads = 2
print(ui)

world = sim.world
world.size = [3 * m, 3 * m, 3 * m]
world.material = "G4_AIR"

waterbox = sim.add_volume("Box", "Waterbox")
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = "G4_WATER"

p = sim.get_physics_user_info()
# p.physics_list_name = "QGSP_BERT_EMV"
p.physics_list_name = "G4EmStandardPhysics_option4"
cuts = p.production_cuts
um = gate.g4_units("um")
cuts.world.gamma = 700 * um
cuts.world.electron = 700 * um
cuts.world.positron = 700 * um
cuts.world.proton = 700 * um

source = sim.add_source("Generic", "Default")
source.particle = "gamma"
source.energy.mono = 80 * keV
source.direction.type = "momentum"
source.direction.momentum = [0, 0, 1]
source.n = 200000

stats = sim.add_actor("SimulationStatisticsActor", "Stats")
stats.track_types_flag = True


def init(sim):
    print("in init")
    sim.initialize()


p = Process(target=init, args=(sim.volume_manager,))

print(p)
p.start()
p.join()

print("---------- end")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 15:54:30 2023

@author: fava
"""

import opengate as gate
import numpy as np
from opengate.tests import utility


paths = utility.get_default_test_paths(__file__, "test050_let_actor_letd", "test050")


sim = gate.Simulation()
ui = sim.user_info
# ui.verbose_level = gate.DEBUG
# ui.running_verbose_level = gate.RUN
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = "MersenneTwister"
ui.random_seed = "auto"


m = gate.g4_units.m
cm = gate.g4_units.cm
mm = gate.g4_units.mm
mrad = gate.g4_units.mrad
km = gate.g4_units.km
MeV = gate.g4_units.MeV
Bq = gate.g4_units.Bq


world = sim.world
world.size = [3 * m, 3 * m, 3 * m]
world.material = "G4_AIR"

waterbox = sim.add_volume("Box", "Waterbox")
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = "G4_WATER"

sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"
sim.physics_manager.set_production_cut("world", "all", 1000 * km)

# EmCalc actor
em_calc = sim.add_actor("EmCalculatorActor", "test")
em_calc.mother = waterbox.name
em_calc.is_ion = True
em_calc.particle_name = "GenericIon"
em_calc.ion_params = "3 7"
em_calc.material = "G4_WATER"
em_calc.nominal_energies = list(np.logspace(np.log10(1e-3), np.log10(1e3), 1000))
em_calc.savefile_path = "/home/fava/Desktop/dedx_table_3_7.txt"


stats = sim.add_actor("SimulationStatisticsActor", "Stats")
stats.track_types_flag = True

sim.run()

print(stats)

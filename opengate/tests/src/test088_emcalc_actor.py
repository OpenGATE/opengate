#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 15:54:30 2023

@author: fava
"""

import opengate as gate
import numpy as np
import re
from opengate.tests import utility


def read_table(path, skip_lines=4):
    table = dict()  # k: energy, v: dedx
    with open(path, "r") as f:
        lines = f.readlines()
    lines = lines[skip_lines:]
    lines = [
        re.findall(r"\d+\.\d+(?:[eE][+-]?\d+)?|\d+(?:[eE][+-]?\d+)?", l) for l in lines
    ]
    for l in lines:
        table[float(l[0])] = float(l[1])

    return table


paths = utility.get_default_test_paths(__file__, "test088_emcalc_actor", "test088")


sim = gate.Simulation()
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = "MersenneTwister"
ui.random_seed = "auto"

m = gate.g4_units.m
cm = gate.g4_units.cm
km = gate.g4_units.km

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
em_calc.attached_to = waterbox.name
em_calc.is_ion = True
# em_calc.particle_name = 'GenericIon'
em_calc.ion_params = "1 1"
em_calc.material = "G4_WATER"
# em_calc.nominal_energies = list(np.logspace(np.log10(1e-3), np.log10(1e3), 1000))
em_calc.nominal_energies = [10, 1e2, 1e3]
em_calc.savefile_path = paths.output / "dedx_table_H.txt"

stats = sim.add_actor("SimulationStatisticsActor", "Stats")
stats.track_types_flag = True

sim.run()

# compare against PSTAR table for protons in liquid water for some energies
pstar_tab_path = paths.output_ref / "PSTAR_table_water.txt"

ref_table = read_table(pstar_tab_path, skip_lines=5)
actor_table = read_table(paths.output / "dedx_table_H.txt", skip_lines=4)

is_ok = True
delta_thresh = 0.05

for e, dedx_actor in actor_table.items():
    if e in ref_table:
        dedx_ref = ref_table[e]
        delta_dedx_rel = abs(dedx_actor - dedx_ref) / dedx_ref
        is_ok = delta_dedx_rel <= delta_thresh and is_ok

utility.test_ok(is_ok)

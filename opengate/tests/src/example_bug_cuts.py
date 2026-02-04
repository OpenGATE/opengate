#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  2 09:48:30 2025

@author: fava
"""

import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility
import opengate_core as g4


def simuation_IDD(production_cuts):
    paths = utility.get_default_test_paths(__file__, "gate_test044_pbs")

    # units
    eV = g4_units.eV
    MeV = g4_units.MeV
    cm = g4_units.cm
    mm = g4_units.mm

    # create simulation object
    sim = gate.Simulation()
    # sim.number_of_threads = 4
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 10 * cm]
    phantom.translation = [-5 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    test_material_name = "Water"
    phantom_off = sim.add_volume("Box", "phantom_off")
    phantom_off.mother = phantom.name
    phantom_off.size = [100 * mm, 60 * mm, 60 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    phantom_off.material = test_material_name
    phantom_off.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_HP_EMZ"
    for p, v in production_cuts.items():
        sim.physics_manager.set_production_cut("world", p, v * mm)
    print(sim.physics_manager.dump_production_cuts())

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 1424 * MeV
    source.particle = "ion 6 12"

    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.radius = 4 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    # print(dir(source.energy))
    source.n = 1e3
    # source.activity = 100 * kBq

    # stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True
    # stat.output_filename =  'stats.txt'
    sim.run(start_new_process=True)
    print(stat)
    output = stat.user_output.stats
    counts = output.merged_data

    return counts


if __name__ == "__main__":
    m = g4_units.m
    mm = g4_units.mm
    print("------ HIGH CUTS simulation ---------")
    production_cuts = {
        "gamma": 1000 * m,
        "electron": 1000 * m,
        "positron": 1000 * m,
        "proton": 1000 * m,
    }

    counts_high_cut = simuation_IDD(production_cuts)

    print("------ LOW CUTS simulation ---------")
    production_cuts = {
        "gamma": 0.1 * mm,
        "electron": 0.1 * mm,
        "positron": 0.1 * mm,
        "proton": 0.1 * mm,
    }

    counts_low_cut = simuation_IDD(production_cuts)

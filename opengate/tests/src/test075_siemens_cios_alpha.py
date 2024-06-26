#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.carm.siemensciosalpha as ciosalpha
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import numpy as np
import uproot
import matplotlib.pyplot as plt

if __name__ == "__main__":
    # paths
    paths = utility.get_default_test_paths(__file__, output_folder="test075_siemens_cios_alpha")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = True
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.random_seed = 12345678
    sim.check_volumes_overlap = True

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    deg = gate.g4_units.deg

    # world
    world = sim.world
    world.size = [5* m, 5 * m, 5 * m]
    world.material = "G4_AIR"

    # add a carm
    carm = ciosalpha.add_carm(sim, "cios_alpha")
    carm.rotation = Rotation.from_euler("ZYX", [0,20,180], degrees=True).as_matrix()

    # xray tube spectrum parameters
    # tube potential [kV]
    kvp = 100

    # add carm source
    source = ciosalpha.add_carm_source(sim, carm.name, kvp)
    source.n = 1e6
    if sim.visu:
        source.n = 1

    # opening of the collimators [0, 50 *mm]
    ciosalpha.update_collimation(sim, carm.name, 20 * mm, 20 * mm)

    # aluminum table
    table = sim.add_volume("Box", "aluminum_table")
    table.size = [60 * cm, 2 * m, 0.9 * mm ]
    table.material = "G4_Al"
    table.translation = [0 * m, 0 * cm, 0 * cm]
    table.color = [0.8, 0.8, 0.8, 1]

    # start simulation
    sim.run()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.contrib.carm.siemensciosalpha import Ciosalpha
from scipy.spatial.transform import Rotation


if __name__ == "__main__":
    # paths
    # paths = utility.get_default_test_paths(__file__, output_folder="test075_siemens_cios_alpha")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "vrml"
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
    world.size = [5 * m, 5 * m, 5 * m]
    world.material = "G4_AIR"

    # xray tube spectrum parameters
    # tube potential [kV]
    kvp = 100

    # add a carm
    carm = Ciosalpha(sim, kvp, source_only=False)
    carm.rotation = Rotation.from_euler("ZYX", [0, 20, 0], degrees=True).as_matrix()
    carm.translation = [0 * cm, 0 * cm, 0 * cm]
    carm.collimation = [25 * mm, 25 * mm]

    carm.source.n = 1e6
    if sim.visu:
        carm.source.n = 1000

    # aluminum table
    table = sim.add_volume("Box", "aluminum_table")
    table.size = [60 * cm, 2 * m, 0.9 * mm]
    table.material = "G4_Al"
    table.translation = [0 * m, 0 * cm, 0 * cm]
    table.color = [0.8, 0.8, 0.8, 1]

    # start simulation
    sim.run()

    # TODO: Test

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import pathlib

if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()
    paths = utility.get_default_test_paths(__file__)

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False

    path_to_json_file = paths.output / "test065_sim.json"

    with open(path_to_json_file, "r") as f:
        dct = gate.serialization.load_json(f)

    sim.from_json_file(path_to_json_file)

    # add a material database
    sim.add_material_database(pathFile / ".." / "data" / "GateMaterials.db")

    print("Regions")
    for r in sim.physics_manager.regions.values():
        print(r)

    print("VolumeManager")
    print(sim.volume_manager)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import pathlib

if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False

    # add a material database
    sim.add_material_database(pathFile / ".." / "data" / "GateMaterials.db")

    #  change world size
    m = gate.g4_units.m
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]

    # add a simple volume
    waterbox = sim.add_volume("Box", "Waterbox")
    cm = gate.g4_units.cm
    waterbox.size = [60 * cm, 60 * cm, 60 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 35 * cm]
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]  # blue

    # another (child) volume with rotation
    mm = gate.g4_units.mm
    sheet = sim.add_volume("Box", "Sheet")
    sheet.size = [30 * cm, 30 * cm, 2 * mm]
    sheet.mother = "Waterbox"
    sheet.material = "Lead"
    r = Rotation.from_euler("x", 33, degrees=True)
    center = [0 * cm, 0 * cm, 10 * cm]
    t = gate.geometry.utility.get_translation_from_rotation_with_center(r, center)
    sheet.rotation = r.as_matrix()
    sheet.translation = t + [0 * cm, 0 * cm, -18 * cm]
    sheet.color = [1, 0, 0, 1]  # red

    # A sphere
    sph = sim.add_volume("Sphere", "mysphere")
    sph.rmax = 5 * cm
    sph.mother = "Waterbox"
    sph.translation = [0 * cm, 0 * cm, -8 * cm]
    sph.material = "Lung"
    sph.color = [0.5, 1, 0.5, 1]  # kind of green
    sph.toto = "nothing"  # ignored, should raise a warning

    # A ...thing ?
    trap = sim.add_volume("Trap", "mytrap")
    trap.mother = "Waterbox"
    trap.translation = [0, 0, 15 * cm]
    trap.material = "G4_LUCITE"

    json_string = sim.dump_as_json_string()
    print(json_string)
    print("******")
    print(gate.serialization.loads_json(json_string))

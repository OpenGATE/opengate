#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from opengate.utility import g4_units


def add_macaco1_materials(sim):
    """
    Adds the Macaco materials database to the simulation if not already present.
    """
    db_folder = Path(__file__).parent.resolve()
    db_filename = db_folder / "macaco_materials.db"
    if not db_filename in sim.volume_manager.material_database.filenames:
        sim.volume_manager.add_material_database(db_filename)


def add_macaco1_camera(sim, name="macaco1"):
    """
    Adds a MACACO1 camera to the simulation.
    FIXME: TO BE MODIFIED AS THE REAL MACACO1 CAMERA
    """

    # units
    cm = g4_units.cm

    # material
    add_macaco1_materials(sim)

    # Bounding box
    camera = sim.add_volume("Box", f"{name}_camera")
    camera.material = "G4_AIR"
    camera.size = [4 * cm, 4 * cm, 7.6 * cm]
    camera.translation = [0, 0, 8.3 * cm]
    camera.color = [1, 1, 1, 1]  # white

    # Scatterer
    scatterer = sim.add_volume("Box", f"{name}_scatterer")
    scatterer.mother = camera
    scatterer.material = "LYSO-Ce-Hilger"
    scatterer.size = [2.72 * cm, 2.68 * cm, 0.5 * cm]
    scatterer.translation = [0, 0, -2.75 * cm]
    scatterer.color = [0, 0, 1, 1]  # blue

    # Absorber
    absorber = sim.add_volume("Box", f"{name}_absorber")
    absorber.mother = camera
    absorber.material = "LYSO-Ce-Hilger"
    absorber.size = [3.24 * cm, 3.6 * cm, 1.0 * cm]
    absorber.translation = [0, 0, 2.5 * cm]
    absorber.color = [1, 0, 0, 1]  # red

    return camera

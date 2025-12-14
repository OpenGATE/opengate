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
    - Bounding box (BB_box)
    - Plane 1 (scatterer side): holder, crystal carcass, PCB, SiPM, LaBr3_VLC crystal
    - Plane 2 (absorber side): holder, crystal carcass, PCB, SiPM, LaBr3_VLC crystal
    """

    # units
    mm = g4_units.mm
    cm = g4_units.cm

    # material
    add_macaco1_materials(sim)

    # BB box (acts as camera envelope)
    camera = sim.add_volume("Box", f"{name}_BB_box")
    camera.mother = sim.world
    camera.material = "G4_AIR"
    camera.size = [16 * cm, 40 * cm, 7.6 * cm]
    camera.translation = [0, 0, 8.3 * cm]
    camera.color = [0.1, 0.1, 0.1, 0.1]

    # Scatterer
    holder1 = sim.add_volume("Box", f"{name}_Holder1")
    holder1.mother = camera.name
    holder1.material = "G4_PLASTIC_SC_VINYLTOLUENE"
    holder1.size = [6.2 * cm, 6.2 * cm, 0.56 * cm]
    holder1.translation = [0, 0, -2.74 * cm]
    holder1.color = [0.1, 0.1, 0.1, 0.9]

    crys_carcase_scatt = sim.add_volume("Box", f"{name}_crysCarcaseScatt")
    crys_carcase_scatt.mother = holder1.name
    crys_carcase_scatt.material = "G4_Al"
    crys_carcase_scatt.size = [2.72 * cm, 2.68 * cm, 0.01 * cm]
    crys_carcase_scatt.translation = [0, 0, -0.265 * cm]

    pcb_scatt = sim.add_volume("Box", f"{name}_PCBScatt")
    pcb_scatt.mother = camera.name
    pcb_scatt.material = "PCB"
    pcb_scatt.size = [10.89 * cm, 20.7 * cm, 0.4 * cm]
    pcb_scatt.translation = [0, 6.25 * cm, -2.26 * cm]
    pcb_scatt.color = [0.0, 0.5, 0.0, 0.9]

    sipm_scatt = sim.add_volume("Box", f"{name}_SiPMScatt")
    sipm_scatt.mother = holder1.name
    sipm_scatt.material = "G4_Si"
    sipm_scatt.size = [2.72 * cm, 2.68 * cm, 0.04 * cm]
    sipm_scatt.translation = [0, 0, 0.26 * cm]
    sipm_scatt.color = [1.0, 0.5, 0.0, 0.9]

    scatterer = sim.add_volume("Box", f"{name}_scatterer")
    scatterer.mother = holder1.name
    scatterer.material = "LaBr3_VLC"
    scatterer.size = [2.72 * cm, 2.68 * cm, 0.50 * cm]
    scatterer.translation = [0, 0, -0.01 * cm]
    scatterer.color = [0.4, 0.7, 1.0, 1.0]

    # Absorber
    holder2 = sim.add_volume("Box", f"{name}_Holder2")
    holder2.mother = camera.name
    holder2.material = "G4_PLASTIC_SC_VINYLTOLUENE"
    holder2.size = [8.0 * cm, 8.0 * cm, 1.06 * cm]
    holder2.translation = [0, 0, 2.51 * cm]
    holder2.color = [0.1, 0.1, 0.1, 0.9]

    crys_carcase_abs = sim.add_volume("Box", f"{name}_crysCarcaseAbs")
    crys_carcase_abs.mother = holder2.name
    crys_carcase_abs.material = "G4_Al"
    crys_carcase_abs.size = [3.24 * cm, 3.60 * cm, 0.01 * cm]
    crys_carcase_abs.translation = [0, 0, -0.515 * cm]

    absorber = sim.add_volume("Box", f"{name}_absorber")
    absorber.mother = holder2.name
    absorber.material = "LaBr3_VLC"
    absorber.size = [3.24 * cm, 3.60 * cm, 1.00 * cm]
    absorber.translation = [0, 0, -0.01 * cm]
    absorber.color = [0.4, 0.7, 1.0, 1.0]

    sipm_abs = sim.add_volume("Box", f"{name}_SiPMAbs")
    sipm_abs.mother = holder2.name
    sipm_abs.material = "G4_Si"
    sipm_abs.size = [3.24 * cm, 3.60 * cm, 0.04 * cm]
    sipm_abs.translation = [0, 0, 0.51 * cm]
    sipm_abs.color = [1.0, 0.5, 0.0, 0.9]

    pcb_abs = sim.add_volume("Box", f"{name}_PCBAbs")
    pcb_abs.mother = camera.name
    pcb_abs.material = "PCB"
    pcb_abs.size = [9.54 * cm, 16.0 * cm, 0.4 * cm]
    pcb_abs.translation = [0, 4.50 * cm, 3.24 * cm]
    pcb_abs.color = [0.0, 0.5, 0.0, 0.9]

    return {
        "camera": camera,
        "scatterer": scatterer,
        "absorber": absorber,
        "holder1": holder1,
        "holder2": holder2,
    }

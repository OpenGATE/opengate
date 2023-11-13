#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import pathlib


if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()
    paths = utility.get_default_test_paths(__file__)
    paths_test009 = utility.get_default_test_paths(__file__, "gate_test009_voxels")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.store_json_archive = True
    sim.store_input_files = True
    sim.output_dir = paths.output / "test065"

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
    sim.physics_manager.set_production_cut(
        volume_name=trap.name, value=1.78 * gate.g4_units.MeV, particle_name="proton"
    )

    # FIXME: size and shape
    b1 = sim.volume_manager.create_volume("BoxVolume", name="b1")
    b2 = sim.add_volume("BoxVolume", name="b2")
    b1_b2 = gate.geometry.volumes.subtract_volumes(b1, b2, translation=[0.1 * cm, 0, 0])
    sim.add_volume(b1_b2)

    patient = sim.add_volume("Image", "patient")
    patient.image = paths.data / "patient-4mm.mhd"
    patient.mother = "world"
    patient.material = "G4_AIR"  # material used by default
    patient.voxel_materials = [
        [-2000, -900, "G4_AIR"],
        [-900, -100, "Lung"],
        [-100, 0, "G4_ADIPOSE_TISSUE_ICRP"],
        [0, 300, "G4_TISSUE_SOFT_ICRP"],
        [300, 800, "G4_B-100_BONE"],
        [800, 6000, "G4_BONE_COMPACT_ICRU"],
    ]

    sim.to_json_file()

    # *****
    json_string = sim.to_json_string()
    reloaded_dict = gate.serialization.loads_json(json_string)

    print(json_string)
    print("******")
    print(reloaded_dict)

    print("Regions before")
    for r in sim.physics_manager.regions.values():
        print(r)

    sim.physics_manager.set_production_cut(
        volume_name=trap.name, value=2.05 * gate.g4_units.MeV, particle_name="proton"
    )
    sim.physics_manager.set_production_cut(
        volume_name=sheet.name, value=27.1 * gate.g4_units.MeV, particle_name="electron"
    )
    print("Regions after change")
    for r in sim.physics_manager.regions.values():
        print(r)

    print("VM before")
    print(sim.volume_manager.volumes.keys())

    sim.volume_manager.volumes.pop("mytrap")
    sim.volume_manager.volumes.pop("b2")
    print("VM after removing volumes")
    print(sim.volume_manager.volumes.keys())

    sim.from_dictionary(reloaded_dict)

    print("Regions after reloading")
    for r in sim.physics_manager.regions.values():
        print(r)

    print("VM after reloading from dict")
    print(sim.volume_manager.volumes.keys())

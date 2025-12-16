#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.geometry.materials import MaterialDatabase
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="gate_test009_voxels", output_folder="test009"
    )

    # create the simulation
    sim = gate.Simulation()

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm
    gcm3 = gate.g4_units.g_cm3
    is_ok = True

    # image
    image_volume = sim.add_volume("Image", "test1")
    image_volume.image = paths.data / "patient-4mm.mhd"
    image_volume.material = "G4_AIR"  # material used by default
    f1 = str(paths.gate_data / "Schneider2000MaterialsTable.txt")
    f2 = str(paths.gate_data / "Schneider2000DensitiesTable.txt")
    tol = 0.08 * gcm3
    vm, materials = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
    image_volume.voxel_materials = vm

    # write mat and label-to-mat
    image_volume.write_material_database(paths.output / "test1.db")
    image_volume.write_label_to_material(paths.output / "test1.json")

    # read back
    sim.volume_manager.add_material_database(paths.output / "test1.db")
    vm = image_volume.voxel_materials.copy()
    image_volume.read_label_to_material(paths.output / "test1.json")
    print(f"Number of materials in the image: {len(vm)}")
    if image_volume.voxel_materials != vm:
        b = False
        utility.print_test(b, f"Error in the label to material {vm} ")
        utility.print_test(b, f"Error in the label to material {a}")
        is_ok = False

    # image
    image_volume = sim.add_volume("Image", "test2")
    image_volume.image = paths.data / "patient-4mm.mhd"
    image_volume.material = "G4_AIR"  # material used by default
    image_volume.voxel_materials = [
        [-2000, -900, "G4_AIR"],
        [-900, -100, "Lung"],
        [-100, 0, "G4_ADIPOSE_TISSUE_ICRP"],
        [0, 300, "G4_TISSUE_SOFT_ICRP"],
        [300, 800, "G4_B-100_BONE"],
        [800, 6000, "G4_BONE_COMPACT_ICRU"],
    ]
    image_volume.write_material_database(paths.output / "test2.db")
    image_volume.write_label_to_material(paths.output / "test2.json")

    # read back
    sim.volume_manager.add_material_database(paths.output / "test2.db")
    vm = image_volume.voxel_materials.copy()
    image_volume.read_label_to_material(paths.output / "test2.json")
    print(f"Number of materials in the image: {len(vm)}")
    if image_volume.voxel_materials != vm:
        b = False
        utility.print_test(b, f"Error in the label to material {vm} ")
        utility.print_test(b, f"Error in the label to material {a}")
        is_ok = False

    utility.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import opengate as gate
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test032")

    # create the simulation
    sim = gate.Simulation()
    sim.output_dir = paths.output

    # shhhht !
    gate.logger.log.setLevel(gate.logger.NONE)

    m = gate.g4_units.m
    cm = gate.g4_units.cm

    # world
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # add a iec phantom
    iec = gate_iec.add_iec_phantom(sim)

    extra_sphere = sim.add_volume("Sphere", name="extra_sphere")
    extra_sphere.rmax = 2 * gate.g4_units.cm
    extra_sphere.translation = [20 * cm, 20 * cm, 20 * cm]

    print("Automatic voxelization entire geometry")
    # voxelize the geometry with 3x3x3 mm spacing
    labels_auto, image_auto = sim.voxelize_geometry(filename="test032_auto")
    info = gate.image.get_info_from_image(image_auto)
    print(f"Image (IEC and sphere): {info.size} {info.spacing} {info.origin}")

    print("Voxelization 3 mm")
    # voxelize the geometry with 3x3x3 mm spacing
    labels_3mm, image_3mm = sim.voxelize_geometry(
        iec, spacing=(3, 3, 3), margin=1, filename="test032_3mm"
    )
    info = gate.image.get_info_from_image(image_3mm)
    print(f"Image (3 mm spacing): {info.size} {info.spacing} {info.origin}")

    print("Voxelization 1 mm")
    # voxelize the geometry with 1x1x1 mm spacing
    labels_1mm, image_1mm, path_to_image_1mm = sim.voxelize_geometry(
        iec, spacing=(1, 1, 1), margin=1, filename="test032_1mm", return_path=True
    )
    info = gate.image.get_info_from_image(image_1mm)
    print(f"Image (1 mm spacing): {info.size} {info.spacing} {info.origin}")

    # read and compare labels
    gate.exception.warning("\nDifference labels")
    with open(paths.output_ref / "test032_labels.json", "r") as f:
        ref_labels = json.load(f)
    added, removed, modified, same = utility.dict_compare(ref_labels, labels_1mm)
    is_ok = len(added) == 0 and len(removed) == 0 and len(modified) == 0
    utility.print_test(is_ok, f"Labels comparisons, added:    {added}")
    utility.print_test(is_ok, f"Labels comparisons, removed:  {removed}")
    utility.print_test(is_ok, f"Labels comparisons: modified: {modified}")

    # compare images
    gate.exception.warning("\nDifference with ref image")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test032_iec.mhd",
            path_to_image_1mm,
            stats=None,
            tolerance=0.01,
        )
        and is_ok
    )

    utility.test_ok(is_ok)

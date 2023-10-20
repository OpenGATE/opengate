#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import json
import opengate as gate
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test032")

    # create the simulation
    sim = gate.Simulation()

    # shhhht !
    gate.logger.log.setLevel(gate.logger.NONE)

    # world
    m = gate.g4_units.m
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # add a iec phantom
    iec = gate_iec.add_iec_phantom(sim)

    # create an empty image with the size (extent) of the volume
    # add one pixel margin
    image = gate.image.create_image_with_volume_extent(
        sim, iec.name, spacing=[3, 3, 3], margin=1
    )
    info = gate.image.get_info_from_image(image)
    print(f"Image : {info.size} {info.spacing} {info.origin}")

    # we need a simulation engine to voxelize a volume
    # (we will reuse the engine, so it need to not be in a subprocess)
    # create the engine in a context, i.e. with ... as ...:
    # That will close the engine correctly once done
    with gate.engines.SimulationEngine(sim) as se:
        se.initialize()

        # voxelized a volume
        print("Starting voxelization ...")
        labels, image = gate.image.voxelize_volume(se, image)
        print(f"Output labels: {labels}")

        # write labels
        lf = str(paths.output / "test032_labels_3mm.json")
        outfile = open(lf, "w")
        json.dump(labels, outfile, indent=4)

        # write image
        f = paths.output / "test032_iec_3mm.mhd"
        print(f"Write image {f}")
        itk.imwrite(image, str(f))

        #
        # redo the same but with 1 mm spacing
        #

        # create an empty image with the size (extent) of the volume
        # add one pixel margin
        image = gate.image.create_image_with_volume_extent(
            sim, iec.name, spacing=[1, 1, 1], margin=1
        )
        info = gate.image.get_info_from_image(image)
        print(f"Image : {info.size} {info.spacing} {info.origin}")

        # voxelized a volume
        print("Starting voxelization ...")
        labels, image = gate.image.voxelize_volume(se, image)
        print(f"Output labels: {labels}")

    # write labels
    lf = str(paths.output / "test032_labels.json")
    outfile = open(lf, "w")
    json.dump(labels, outfile, indent=4)

    # write image
    f = paths.output / "test032_iec.mhd"
    print(f"Write image {f}")
    itk.imwrite(image, str(f))

    # read and compare labels
    gate.exception.warning("\nDifference labels")
    ref_labels = open(paths.output_ref / "test032_labels.json").read()
    ref_labels = json.loads(ref_labels)
    added, removed, modified, same = utility.dict_compare(ref_labels, labels)
    is_ok = len(added) == 0 and len(removed) == 0 and len(modified) == 0
    utility.print_test(is_ok, f"Labels comparisons, added:    {added}")
    utility.print_test(is_ok, f"Labels comparisons, removed:  {removed}")
    utility.print_test(is_ok, f"Labels comparisons: modified: {modified}")

    # compare images
    gate.exception.warning("\nDifference with ref image")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test032_iec.mhd", f, stats=None, tolerance=0.01
        )
        and is_ok
    )

    utility.test_ok(is_ok)

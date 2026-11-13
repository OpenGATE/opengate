#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
voxelize_geometry with an extent given as two corners (tuples or numpy arrays),
and the margin (in voxels): the image is centred on the extent (#1222).
"""

import itk
import numpy as np
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test143")

    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE

    mm = gate.g4_units.mm
    cm = gate.g4_units.cm

    sim.world.size = [50 * cm, 50 * cm, 50 * cm]
    sim.world.material = "G4_AIR"
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [10 * cm, 10 * cm, 10 * cm]
    waterbox.material = "G4_WATER"

    spacing = np.array([4, 4, 4]) * mm
    is_ok = True

    def check(name, image, size, origin):
        info = gate.image.get_info_from_image(image)
        print(f"{name}: size {info.size} origin {info.origin}")
        ok = np.array_equal(info.size, size) and np.allclose(info.origin, origin)
        utility.print_test(ok, f"{name}: size {size} origin {origin}")
        # the image is centred on the box: centre of the voxel grid at 0
        centre = info.origin + (info.size - 1) / 2 * info.spacing
        c = np.allclose(centre, 0)
        utility.print_test(c, f"{name}: image centred at {centre}")
        return ok and c

    # extent given as two corners (tuples), as in the documentation
    lo = (-60 * mm, -60 * mm, -60 * mm)
    hi = (60 * mm, 60 * mm, 60 * mm)
    _, image = sim.voxelize_geometry(extent=(lo, hi), spacing=spacing)
    is_ok = check("corners (tuples)", image, [30, 30, 30], [-58, -58, -58]) and is_ok

    # extent given as two numpy arrays
    _, image = sim.voxelize_geometry(
        extent=(np.array(lo), np.array(hi)), spacing=spacing
    )
    is_ok = check("corners (arrays)", image, [30, 30, 30], [-58, -58, -58]) and is_ok

    # extent given as a volume, with a margin of 2 voxels on each side:
    # 25 + 2 x 2 voxels, the first voxel centre at -50 + 2 - 2 x 4 mm
    labels, image = sim.voxelize_geometry(extent=waterbox, spacing=spacing, margin=2)
    is_ok = check("volume + margin", image, [29, 29, 29], [-56, -56, -56]) and is_ok

    # the margin is air, the centre is water
    arr = itk.array_view_from_image(image)
    print(f"Labels: {labels}")
    air, water = labels["world"]["label"], labels["waterbox"]["label"]
    m = arr[0, 0, 0] == air and arr[1, 1, 1] == air and arr[2, 2, 2] == water
    m = m and arr[14, 14, 14] == water and arr[26, 26, 26] == water
    m = m and arr[27, 27, 27] == air
    utility.print_test(m, "margin voxels are air, the box voxels are water")
    is_ok = is_ok and m

    utility.test_ok(is_ok)

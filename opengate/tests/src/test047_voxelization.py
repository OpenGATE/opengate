#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import time
import itk
import numpy as np

paths = gate.get_default_test_paths(__file__)

n = int(1e5)

# read img
f = paths.data / "source_three_areas_crop_3.5mm.mhd"
img = itk.imread(str(f))


def test_voxelized(img, version):
    # create voxelized sampling
    v = gate.VoxelizedSourcePDFSampler(img, version=version)
    start = time.time()
    if version == 1:
        i, j, k = v.sample_indices(n)
    else:
        i, j, k = v.sample_indices_slower(n)
    end = time.time()
    print(f"Version {version}: done in {end - start:0.3f} sec")

    # create output image
    imga = itk.array_view_from_image(img)
    outa = np.zeros_like(imga)
    for a, b, c in zip(i, j, k):
        outa[a, b, c] += 1
    out = itk.image_from_array(outa)
    out.CopyInformation(img)
    # itk.imwrite(out, f"test047_vox_{version}.mhd")

    # test : compare with initial image
    nn = outa[imga != 0].sum()
    zz = outa[imga == 0].sum()
    is_ok = nn == n and zz == 0

    if not is_ok:
        gate.print_test(is_ok, f"Version {version}: ERROR ! {nn}/{n} and {zz}/0")
    else:
        gate.print_test(is_ok, f"Version {version}: test OK")

    return is_ok


is_ok = test_voxelized(img, 1)
is_ok = test_voxelized(img, 2) and is_ok
is_ok = test_voxelized(img, 3) and is_ok

gate.test_ok(is_ok)

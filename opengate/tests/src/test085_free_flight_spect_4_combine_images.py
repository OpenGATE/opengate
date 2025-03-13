#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
import SimpleITK as sitk
import numpy as np
import subprocess
import os, sys

if __name__ == "__main__":

    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test085_spect"
    )

    # not on windows
    if os.name == "nt":
        sys.exit(0)

    # The test needs the output of the other tests
    if not os.path.isfile(paths.output / "projection_1_ff.mhd"):
        subprocess.call(
            ["python", paths.current / "test085_free_flight_spect_2_ff_mt.py"]
        )
    if not os.path.isfile(paths.output / "projection_1_ff_sc.mhd"):
        subprocess.call(
            ["python", paths.current / "test085_free_flight_spect_3_scatter_mt.py"]
        )
    #
    prim_filename = paths.output / "projection_1_ff.mhd"
    sca_filename = paths.output / "projection_1_ff_sc.mhd"
    ref_n = 5e6
    prim_n = 2e5
    sca_n = 4e4
    scaling_prim = ref_n / prim_n
    scaling_sc = ref_n / sca_n

    # read images
    prim_img = sitk.ReadImage(prim_filename)
    sca_img = sitk.ReadImage(sca_filename)

    print("Number of events, ref = ", ref_n)
    print("Number of events, ff = ", prim_n, scaling_prim)
    print("Number of events, sc = ", sca_n, scaling_sc)

    # sum both images
    arr = (
        sitk.GetArrayFromImage(prim_img) * scaling_prim
        + sitk.GetArrayFromImage(sca_img) * scaling_sc
    )
    img = sitk.GetImageFromArray(arr)
    img.CopyInformation(prim_img)
    sitk.WriteImage(img, paths.output / "projection_1_total.mhd")

    # compare to noFF
    is_ok = True
    for i in range(0, 2):
        print()
        is_ok = (
            utility.assert_images(
                paths.output_ref / "projection_1_ref.mhd",
                paths.output / "projection_1_ff.mhd",
                None,
                tolerance=np.inf,
                ignore_value_data1=0,
                sum_tolerance=np.inf,
                axis="x",
                scaleImageValuesFactor=scaling_prim,
                slice_id=i,
                fig_name=paths.output / f"projection_1_ff_test_{i}.png",
            )
            and is_ok
        )

        is_ok = (
            utility.assert_images(
                paths.output_ref / "projection_1_ref.mhd",
                paths.output / "projection_1_ff_sc.mhd",
                None,
                tolerance=np.inf,
                ignore_value_data1=0,
                sum_tolerance=np.inf,
                axis="x",
                scaleImageValuesFactor=scaling_sc,
                slice_id=i,
                fig_name=paths.output / f"projection_1_ff_sc_test_{i}.png",
            )
            and is_ok
        )

        is_ok = (
            utility.assert_images(
                paths.output_ref / "projection_1_ref.mhd",
                paths.output / "projection_1_total.mhd",
                None,
                tolerance=130,
                ignore_value_data1=0,
                sum_tolerance=40,
                axis="x",
                sad_profile_tolerance=22,
                slice_id=i,
                fig_name=paths.output / f"projection_1_total_test_{i}.png",
            )
            and is_ok
        )

    utility.test_ok(is_ok)

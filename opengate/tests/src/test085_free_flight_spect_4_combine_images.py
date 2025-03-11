#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
import SimpleITK as sitk

if __name__ == "__main__":

    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test085_spect"
    )

    #
    prim_filename = paths.output / "projection_1_ff.mhd"
    sca_filename = paths.output / "projection_1_ff_sc.mhd"
    ref_n = 2e6
    prim_n = 5e5
    sca_n = 5e4
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
        is_ok = (
            utility.assert_images(
                paths.output / "projection_1_ref.mhd",
                paths.output / "projection_1_ff.mhd",
                None,
                tolerance=65,
                ignore_value_data1=0,
                sum_tolerance=8.5,
                axis="x",
                scaleImageValuesFactor=scaling_prim,
                slice_id=i,
                fig_name=paths.output / f"projection_1_ff_test_{i}.png",
            )
            and is_ok
        )

        is_ok = (
            utility.assert_images(
                paths.output / "projection_1_ref.mhd",
                paths.output / "projection_1_ff_sc.mhd",
                None,
                tolerance=65,
                ignore_value_data1=0,
                sum_tolerance=8.5,
                axis="x",
                scaleImageValuesFactor=scaling_sc,
                slice_id=i,
                fig_name=paths.output / f"projection_1_ff_sc_test_{i}.png",
            )
            and is_ok
        )

        is_ok = (
            utility.assert_images(
                paths.output / "projection_1_ref.mhd",
                paths.output / "projection_1_total.mhd",
                None,
                tolerance=65,
                ignore_value_data1=0,
                sum_tolerance=8.5,
                axis="x",
                sad_profile_tolerance=10,
                slice_id=i,
                fig_name=paths.output / f"projection_1_total_test_{i}.png",
            )
            and is_ok
        )

    utility.test_ok(False)

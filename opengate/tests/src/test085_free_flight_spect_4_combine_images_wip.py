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
    ref_n = 5e6
    prim_n = 1e6
    sca_n = 1e4
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
        )
        and is_ok
    )

    utility.test_ok(False)

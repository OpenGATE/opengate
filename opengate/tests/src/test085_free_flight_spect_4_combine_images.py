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
    ref_n = 5e5
    prim_n = 5e5
    sca_n = 5e4
    scaling_sc = prim_n / sca_n
    # f = 0

    # read images
    prim_img = sitk.ReadImage(prim_filename)
    sca_img = sitk.ReadImage(sca_filename)

    print("Number of events, ref = ", ref_n)
    print("Number of events, ff = ", prim_n)
    print("Number of events, sc = ", sca_n, scaling_sc)

    # sum both images
    arr = (
        sitk.GetArrayFromImage(prim_img) + sitk.GetArrayFromImage(sca_img) * scaling_sc
    )
    scaling = 1.0
    print("scaling", scaling)
    arr = arr * scaling
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
        )
        and is_ok
    )

    utility.test_ok(False)

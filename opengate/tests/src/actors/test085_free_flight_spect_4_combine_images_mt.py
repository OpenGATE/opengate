#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys

import SimpleITK as sitk

from opengate.tests import utility


def main(dependency="test085_free_flight_spect_2b_fd_mt.py"):
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test085_spect"
    )

    # not on windows
    if os.name == "nt":
        sys.exit(0)

    # The test needs the output of the other tests
    subdir = os.path.dirname(__file__)
    if not os.path.isfile(paths.output / "projection_1_fd_counts.mhd"):
        subprocess.call(["python", paths.current / subdir / dependency])
    if not os.path.isfile(paths.output / "projection_1_ff_sc_counts.mhd"):
        subprocess.call(
            [
                "python",
                paths.current / subdir / "test085_free_flight_spect_3_scatter_mt.py",
            ]
        )

    # ratios of the number of particles
    ref_n = 5e6
    prim_n = 6e3
    sca_n = 1e4
    scaling_prim = ref_n / prim_n
    scaling_sc = ref_n / sca_n

    # merge primary and scatter
    prim_filename = paths.output / f"projection_1_fd_counts.mhd"
    sca_filename = paths.output / f"projection_1_ff_sc_counts.mhd"

    # read images
    prim_img = sitk.ReadImage(prim_filename)
    sca_img = sitk.ReadImage(sca_filename)

    print("Number of events, ref = ", ref_n)
    print("Number of events, fd = ", prim_n, scaling_prim)
    print("Number of events, sc = ", sca_n, scaling_sc)

    # sum both images
    arr = (
        sitk.GetArrayFromImage(prim_img) * scaling_prim
        + sitk.GetArrayFromImage(sca_img) * scaling_sc
    )
    img = sitk.GetImageFromArray(arr)
    img.CopyInformation(prim_img)
    sitk.WriteImage(img, paths.output / f"projection_1_total.mhd")

    # compare to noFF
    is_ok = True

    print()
    print("fd counts must be lower than ref counts")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_1_ref_counts.mhd",
            paths.output / "projection_1_fd_counts.mhd",
            None,
            tolerance=101,
            ignore_value_data1=0,
            sum_tolerance=45,
            axis="x",
            scaleImageValuesFactor=scaling_prim,
            slice_id=1,
            fig_name=paths.output / f"projection_1_ff_test_1.png",
        )
        and is_ok
    )

    print()
    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_1_ref_counts.mhd",
            paths.output / "projection_1_ff_sc_counts.mhd",
            None,
            tolerance=180,
            ignore_value_data1=0,
            sum_tolerance=48,
            axis="x",
            scaleImageValuesFactor=scaling_sc,
            slice_id=0,
            fig_name=paths.output / f"projection_1_ff_sc_test_1.png",
        )
        and is_ok
    )

    print()
    print(f"Compare the head n1, slice scatter")
    is_ok = (
        utility.assert_images(
            paths.output_ref / f"projection_1_ref_counts.mhd",
            paths.output / f"projection_1_total.mhd",
            None,
            tolerance=180,
            ignore_value_data1=0,
            sum_tolerance=48,
            axis="x",
            sad_profile_tolerance=39,
            slice_id=0,
            fig_name=paths.output / f"projection_1_total_test_scatter.png",
        )
        and is_ok
    )

    print()
    print(f"Compare the head n1, slice primary")
    is_ok = (
        utility.assert_images(
            paths.output_ref / f"projection_1_ref_counts.mhd",
            paths.output / f"projection_1_total.mhd",
            None,
            tolerance=71,
            ignore_value_data1=0,
            sum_tolerance=20,
            axis="x",
            sad_profile_tolerance=30,
            slice_id=1,
            fig_name=paths.output / f"projection_1_total_test_prim.png",
        )
        and is_ok
    )

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()

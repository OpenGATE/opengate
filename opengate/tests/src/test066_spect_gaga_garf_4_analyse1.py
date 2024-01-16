#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from box import Box

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test066")
    output_path = paths.output

    # folders and names
    ref_simu_name = "test066_1_reference"
    ref_output_folder = output_path
    test_simu_name = "test066_2"
    test_output_folder = output_path

    # image filenames
    ref_names = [
        ref_output_folder / f"{ref_simu_name}_0.mhd",
        ref_output_folder / f"{ref_simu_name}_1.mhd",
    ]
    test_names = [
        test_output_folder / f"{test_simu_name}_0.mhd",
        test_output_folder / f"{test_simu_name}_1.mhd",
    ]

    options = Box()
    options.scaling = 2
    options.n_slice = 1
    options.window_width = 33
    options.window_level = 17
    options.crop_center = (63, 73)
    options.crop_width = (100, 100)
    options.hline = 58
    options.vline = 44
    options.width = 10
    options.lab_ref = "GAGA-GARF in Gate"
    options.lab_test = "GAGA-GARF standalone"
    options.title = "Ref vs GAGA-REF in Gate"

    plt = utility.plot_compare_profile(ref_names, test_names, options)

    f = test_output_folder / f"{test_simu_name}.pdf"
    print("Save figure in ", f)
    plt.savefig(f, bbox_inches="tight", format="pdf")

    # test
    print()
    is_ok = True
    for ref_name, test_name in zip(ref_names, test_names):
        is_ok = (
            utility.assert_images(
                ref_name,
                test_name,
                axis="x",
                scaleImageValuesFactor=options.scaling,
                sum_tolerance=12,
                tolerance=110,
            )
            and is_ok
        )

    utility.test_ok(is_ok)

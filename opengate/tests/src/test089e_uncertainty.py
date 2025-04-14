#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from opengate.contrib.spect.spect_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test089")

    # parameters for FF
    simu_name = "test089"
    output_folder = paths.output
    n_prim = 1e8
    n_scatter = 1e7
    n_target = 1e9

    # compute relative uncertainty for primary
    f = output_folder / "primary_uncertainty.mhd"
    prim_uncert, prim_mean, prim_squared_mean = history_rel_uncertainty_from_files(
        output_folder / "test089_primary_0_counts.mhd",
        output_folder / "test089_primary_0_squared_counts.mhd",
        n_prim,
        f,
    )
    print(f)

    # compute relative uncertainty for scatter
    f = output_folder / "scatter_uncertainty.mhd"
    scatter_uncert, scatter_mean, scatter_squared_mean = (
        history_rel_uncertainty_from_files(
            output_folder / "test089_scatter_0_counts.mhd",
            output_folder / "test089_scatter_0_squared_counts.mhd",
            n_scatter,
            f,
        )
    )
    print(f)

    # combined relative uncertainty
    uncert, mean = history_ff_combined_rel_uncertainty(
        prim_mean,
        prim_squared_mean,
        scatter_mean,
        scatter_squared_mean,
        n_prim,
        n_scatter,
    )

    # open image to get the metadata
    prim_img = sitk.ReadImage(f)

    # scaling is according to prim (see in np_history_by_history_ff_combined_relative_uncertainty)
    scaling = n_target / n_prim
    print(f"Primary to scatter ratio = {n_prim/n_scatter:.01f}")
    print(f"Scaling to target        = {scaling:.01f}")
    img = sitk.GetImageFromArray(mean * scaling)
    img.CopyInformation(prim_img)
    fn = output_folder / "mean.mhd"
    sitk.WriteImage(img, fn)
    print(fn)

    # write images
    img = sitk.GetImageFromArray(uncert)
    img.CopyInformation(prim_img)
    fn = output_folder / "relative_uncertainty.mhd"
    sitk.WriteImage(img, fn)
    print(fn)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from opengate.contrib.spect.spect_freeflight_helpers import *
from opengate.contrib.spect.spect_helpers import *


def go():
    paths = utility.get_default_test_paths(__file__, output_folder="test099_pytomo")
    print(paths)
    data_path = paths.data / "test099_pytomo" / "data"
    tomo_path = data_path / "tomo_4.8mm_2e7"

    # input param
    primary_activity = 2e8
    primary_activity = 2e7
    scatter_activity = 1e7
    ref_activity = 1e9
    n_angles = 60
    n_heads = 2

    # combine ffaa primary and scatter + compute relative uncertainty
    merge_freeflight_uncertainty_for_all_heads(
        tomo_path,
        ref_activity,
        ["primary", "scatter"],
        [primary_activity, scatter_activity],
        n_heads,
        verbose=True,
    )

    # combine the heads in to a sinogram and separate by energy channels
    projection_filenames = [
        tomo_path / f"projection_{h}_counts.mhd" for h in range(n_heads)
    ]
    print(projection_filenames)
    sinograms = build_sinograms_from_files(projection_filenames, n_angles)
    for i in range(len(sinograms)):
        sinogram = sinograms[i]
        f = tomo_path / f"sinogram_{i}.mhd"
        sitk.WriteImage(sinogram, f)
        print(f"Written sinogram {f}")


if __name__ == "__main__":
    go()

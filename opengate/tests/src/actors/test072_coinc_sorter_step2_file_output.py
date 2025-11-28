#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.actors.coincidences import coincidences_sorter
import uproot
import os
import numpy as np
import sys
import pandas as pd


def main(dependency="test072_coinc_sorter_step1.py"):

    # If output_singles.root does not exist, run a simulation to generate it
    paths = utility.get_default_test_paths(__file__, output_folder="test072")
    root_filename = paths.output / "output_singles.root"
    if not os.path.exists(root_filename):
        print(f"Simulating singles to create {root_filename} ...")
        subdir = os.path.dirname(__file__)
        os.system(f"python {str(paths.current / subdir / dependency)}")

    # Prepare arguments for the coincidence sorter
    root_file = uproot.open(root_filename)
    singles_tree = root_file["Singles_crystal"]
    ns = gate.g4_units.nanosecond
    time_window = 3 * ns
    transaxial_plane = "xy"
    policy = "removeMultiples"
    mm = gate.g4_units.mm
    minDistanceXY = 0 * mm
    maxDistanceZ = 32 * mm

    # Run coincidence sorter and return concidences as a pandas DataFrame
    coincidences_pd = coincidences_sorter(
        singles_tree,
        time_window,
        policy,
        minDistanceXY,
        transaxial_plane,
        maxDistanceZ,
        return_type="pd",
    )

    # Run coincidence sorter again, saving coincidences to a root file
    coincidences_sorter(
        singles_tree,
        time_window,
        policy,
        minDistanceXY,
        transaxial_plane,
        maxDistanceZ,
        output_file_path=paths.output / "coincidences.root",
        output_file_format="root",  # Could be ommitted since "root" is the default format
    )
    # Read back the coincidences from the root file and remove the colunm named "index"
    with uproot.open(paths.output / "coincidences.root") as file:
        tree = file["Coincidences"]
        coincidences_from_root = tree.arrays(library="pd")
    os.remove(paths.output / "coincidences.root")

    # Coincidence sorter output to HDF5 is supported only in Python 3.10 and higher
    if sys.version_info[1] > 9:
        # Run coincidence sorter again, saving coincidences to a HDF5 file
        coincidences_sorter(
            singles_tree,
            time_window,
            policy,
            minDistanceXY,
            transaxial_plane,
            maxDistanceZ,
            output_file_path=paths.output / "coincidences.hdf5",
            output_file_format="hdf5",
        )
        # Read back the coincidences from the HDF5 file
        coincidences_from_hdf5 = pd.read_hdf(paths.output / "coincidences.hdf5")
        os.remove(paths.output / "coincidences.hdf5")

    # Check that the coincidences from the root file and the HDF5 file are equal to the original DataFrame
    try:
        pd.testing.assert_frame_equal(
            coincidences_from_root,
            coincidences_pd,
            check_dtype=False,
            check_categorical=False,
            check_exact=True,
        )
        # Coincidence sorter output to HDF5 is supported only in Python 3.10 and higher
        if sys.version_info[1] > 9:
            pd.testing.assert_frame_equal(
                coincidences_from_hdf5,
                coincidences_pd,
                check_dtype=False,
                check_categorical=False,
                check_exact=True,
            )
        is_ok = True
    except AssertionError:
        is_ok = False

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()

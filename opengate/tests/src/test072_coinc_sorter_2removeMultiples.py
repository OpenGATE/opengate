#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.actors.coincidences import (
    coincidences_sorter,
    copy_tree_for_dump,
)
import uproot
import subprocess
import os

if __name__ == "__main__":
    # test paths
    paths = utility.get_default_test_paths(
        __file__, output_folder="test072_coinc_sorter"
    )

    # The test needs the output of test072_coinc_sorter_1.py
    # If the output of test072_coinc_sorter_1.py does not exist, create it
    if not os.path.isfile(paths.output / "test72_output_1.root"):
        print("---------- Begin of test072_coinc_sorter_1.py ----------")
        subprocess.call(["python", paths.current / "test072_coinc_sorter_1.py"])
        print("----------- End of test072_coinc_sorter_1.py -----------")

    # open root file
    path_to_rootfile = paths.output / "test72_output_1.root"
    print(f"Opening {path_to_rootfile} ...")
    root_file = uproot.open(path_to_rootfile)

    # consider the tree of "singles"
    singles_tree = root_file["Singles_crystal"]
    n = int(singles_tree.num_entries)
    print(f"There are {n} singles")

    # time windows
    ns = gate.g4_units.nanosecond
    time_window = 3 * ns
    policy = "removeMultiples"

    minSecDiff = 1  # not added yet
    # apply coincidences sorter
    # (chunk size can be much larger, keep a low value to check it is ok)
    coincidences = coincidences_sorter(
        singles_tree, time_window, minSecDiff, policy, chunk_size=1000000
    )
    nc = len(coincidences["GlobalTime1"])
    print(f"There are {nc} coincidences for policy", policy)

    # save to file
    # WARNING root version >= 5.2.2 needed
    output_file = uproot.recreate(paths.output / "coinc2removeMultiples.root")
    output_file["Coincidences"] = coincidences
    output_file["Singles_crystal"] = copy_tree_for_dump(singles_tree)

    nc_ref = 2275
    nc_tol = nc * 0.03  # 3%

    is_ok = utility.check_diff_abs(int(nc), int(nc_ref), tolerance=nc_tol, txt="")

    utility.test_ok(is_ok)

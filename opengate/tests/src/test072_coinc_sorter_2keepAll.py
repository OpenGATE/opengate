#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.actors.coincidences import (
    coincidences_sorter,
    copy_tree_for_dump,
)
import uproot

if __name__ == "__main__":
    # test paths
    paths = utility.get_default_test_paths(
        __file__, output_folder="test072_coinc_sorter"
    )

    # open root file
    root_filename = paths.output / "test72_output_1.root"
    print(f"Opening {root_filename} ...")
    root_file = uproot.open(root_filename)

    # consider the tree of "singles"
    singles_tree = root_file["Singles_crystal"]
    n = int(singles_tree.num_entries)
    print(f"There are {n} singles")
    print(singles_tree.typenames())

    # time windows
    ns = gate.g4_units.nanosecond
    time_window = 300 * ns
    policy = "keepAll"

    minSecDiff = 1  # NOT YET IMPLEMENTED
    # apply coincidences sorter
    # (chunk size can be much larger, keep a low value to check it is ok)
    coincidences = coincidences_sorter(
        singles_tree, time_window, minSecDiff, policy, chunk_size=4000
    )
    nc = len(coincidences["GlobalTime1"])
    print(f"There are {nc} coincidences for policy", policy)

    # save to file
    # WARNING root version >= 5.2.2 needed
    output_file = uproot.recreate(paths.output / "coinc2keepAll.root")
    output_file["Coincidences"] = coincidences
    output_file["Singles_crystal"] = copy_tree_for_dump(singles_tree)

    nc_ref = 5029
    nc_tol = nc * 0.03  # 3%

    is_ok = utility.check_diff_abs(int(nc), int(nc_ref), tolerance=nc_tol, txt="")

    utility.test_ok(is_ok)

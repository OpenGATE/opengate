#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.actors.coincidences import (
    coincidences_sorter_method_1,
    copy_tree_for_dump,
)
import uproot

if __name__ == "__main__":
    # test paths
    paths = utility.get_default_test_paths(
        __file__, output_folder="test72_coinc_sorter"
    )

    # open root file
    root_filename = paths.output / "test72_output_1.root"
    print(f"Opening {root_filename} ...")
    root_file = uproot.open(root_filename)

    # consider the tree of "singles"
    singles_tree = root_file["singles"]
    n = int(singles_tree.num_entries)
    print(f"There are {n} singles")

    print(singles_tree.typenames())

    # time windows
    ns = gate.g4_units.nanosecond
    time_window = 5 * ns

    # apply coincidences sorter
    # (chunk size can be much larger, keep a low value to check it is ok)
    coincidences = coincidences_sorter_method_1(
        singles_tree, time_window, chunk_size=10000
    )
    nc = len(coincidences["GlobalTime1"])
    print(f"There are {nc} coincidences")

    # save to file
    # WARNING root version >= 5.2.2 needed
    output_file = uproot.recreate("output.root")
    output_file["coincidences"] = coincidences
    output_file["singles"] = copy_tree_for_dump(singles_tree)

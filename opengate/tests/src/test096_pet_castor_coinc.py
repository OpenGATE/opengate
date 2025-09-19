#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test096_pet_castor_helpers import *
from opengate.actors.coincidences import coincidences_sorter, copy_tree_for_dump
import os
import sys

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test096_pet_castor_interface"
    )

    # check or create the root file
    root_filename = paths.output / "output_ref.root"
    if not os.path.exists(root_filename):
        dependency = "test096_pet_castor.py"
        # ignore on windows
        if os.name == "nt":
            utility.test_ok(True)
            sys.exit(0)
        cmd = "python " + str(paths.current / dependency)
        r = os.system(cmd)

    # open the root file
    print(f"Opening {root_filename}")
    root_file = uproot.open(root_filename)
    root_folder = root_filename.parent

    # consider the singles and hits trees
    hits_tree = root_file["hits"]
    n = int(hits_tree.num_entries)
    print(f"There are {n} hits")

    singles_tree = root_file["singles"]
    n = int(singles_tree.num_entries)
    print(f"There are {n} singles")

    # time windows
    ns = gate.g4_units.nanosecond
    time_window = 3 * ns
    policy = "takeAllGoods"

    mm = gate.g4_units.mm
    min_trans_dist = 0 * mm
    transaxial_plane = "xy"
    max_trans_dist = 190 * mm
    # apply the coincidence sorter
    coincidences = coincidences_sorter(
        singles_tree,
        time_window,
        policy,
        min_trans_dist,
        transaxial_plane,
        max_trans_dist,
    )
    nc = len(coincidences["GlobalTime1"])
    print(f"There are {nc} coincidences for the policy", policy)

    # save to file
    # WARNING root version >= 5.2.2 needed
    output_filename = root_folder / f"coincidences.root"
    output_file = uproot.recreate(output_filename)
    output_file["coincidences"] = coincidences
    output_file["singles"] = copy_tree_for_dump(singles_tree)
    output_file["hits"] = copy_tree_for_dump(hits_tree)
    print(f"File {output_filename} saved")

    is_ok = False
    utility.test_ok(is_ok)

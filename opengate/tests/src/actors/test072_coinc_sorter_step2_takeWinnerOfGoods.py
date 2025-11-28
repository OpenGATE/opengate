#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.actors.coincidences import coincidences_sorter
from opengate.contrib.root_helpers import *
import uproot
import os
import numpy as np
from scipy.stats import wasserstein_distance
import sys


def main(dependency="test072_coinc_sorter_step1.py"):
    # test paths
    paths = utility.get_default_test_paths(__file__, output_folder="test072")

    # open root file
    root_filename = paths.output / "output_singles.root"
    # this test need output/test072/output_singles.root
    if not os.path.exists(root_filename):
        # ignore on windows
        if os.name == "nt":
            utility.test_ok(True)
            sys.exit(0)
        subdir = os.path.dirname(__file__)
        cmd = "python " + str(paths.current / subdir / dependency)
        r = os.system(cmd)

    # open root file

    print(f"Opening {root_filename} ...")
    root_file = uproot.open(root_filename)

    # consider the tree of "singles"
    singles_tree = root_file["Singles_crystal"]
    n = int(singles_tree.num_entries)
    print(f"There are {n} singles")

    # time windows
    ns = gate.g4_units.nanosecond
    time_window = 3 * ns
    transaxial_plane = "xy"
    policy = "takeWinnerOfGoods"

    mm = gate.g4_units.mm
    minDistanceXY = 0 * mm
    maxDistanceZ = 32 * mm
    # apply coincidences sorter
    # (chunk size can be much larger, keep a low value to check it is ok)
    coincidences = coincidences_sorter(
        singles_tree,
        time_window,
        policy,
        minDistanceXY,
        transaxial_plane,
        maxDistanceZ,
        chunk_size=1000000,
    )
    nc = len(coincidences["GlobalTime1"])
    print(f"There are {nc} coincidences for policy", policy)

    # save to file
    # WARNING root version >= 5.2.2 needed
    output_filename = paths.output / f"output_{policy}.root"
    root_write_trees(
        output_filename, ["coincidences", "singles"], [coincidences, singles_tree]
    )

    # Compare with reference output
    ref_folder = paths.output_ref

    ref_filename = ref_folder / f"{policy}_Gate9.4.root"

    ref_file = uproot.open(ref_filename)
    ref_coincidences = ref_file["Coincidences"]

    nc_ref = int(ref_coincidences.num_entries)
    stat_diff = abs(nc_ref - nc) / nc_ref
    tolerance_stat = 0.05  # 5%
    print(
        f"Stat comparison {nc} (Gate10) vs. {nc_ref} (Gate9.4): {stat_diff}, tolerance {tolerance_stat}"
    )

    both_posX = np.concatenate(
        (coincidences["PostPosition_X1"], coincidences["PostPosition_X2"])
    )
    ref_both_posX = np.concatenate(
        (ref_coincidences["globalPosX1"], ref_coincidences["globalPosX2"])
    )

    both_energy = np.concatenate(
        (coincidences["TotalEnergyDeposit1"], coincidences["TotalEnergyDeposit2"])
    )
    ref_both_energy = np.concatenate(
        (ref_coincidences["energy1"], ref_coincidences["energy2"])
    )

    # Calculate Wasserstein distance for comparison
    distance_posX = wasserstein_distance(both_posX, ref_both_posX)
    tolerance_posX = 3.0
    print(f"Wasserstein distance on X : {distance_posX}, tolerence {tolerance_posX}")

    distance_energy = wasserstein_distance(both_energy, ref_both_energy)
    tolerance_energy = 0.005
    print(
        f"Wasserstein distance on energy : {distance_energy}, tolerence {tolerance_energy}"
    )

    is_ok = (
        stat_diff < tolerance_stat
        and distance_posX < tolerance_posX
        and distance_energy < tolerance_energy
    )

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()

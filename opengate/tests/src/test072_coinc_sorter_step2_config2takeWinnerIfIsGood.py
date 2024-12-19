#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.actors.coincidences import (
    coincidences_sorter,
    copy_tree_for_dump,
)
import uproot
import os
import numpy as np
from scipy.stats import wasserstein_distance

if __name__ == "__main__":
    # test paths
    paths = utility.get_default_test_paths(__file__, output_folder="test072")

    # open root file
    root_filename = paths.output / "output_config2.root"
    # root_filename = "output_config2.root"
    print(f"Opening {root_filename} ...")
    root_file = uproot.open(root_filename)

    # consider the tree of "singles"
    singles_tree = root_file["Singles_crystal"]
    n = int(singles_tree.num_entries)
    print(f"There are {n} singles")

    # print(singles_tree.typenames())

    # time windows
    ns = gate.g4_units.nanosecond
    ms = gate.g4_units.millisecond
    time_window = 3 * ns
    # policy = "keepIfOnlyOneGood"
    policy = "takeWinnerIfIsGood"

    mm = gate.g4_units.mm
    minDistanceXY = 226.27417 * mm  # 160 *sqrt(2) * mm
    maxDistanceZ = 32 * mm  # 32 * mm
    # apply coincidences sorter
    # (chunk size can be much larger, keep a low value to check it is ok)
    coincidences = coincidences_sorter(
        singles_tree,
        time_window,
        policy,
        minDistanceXY,
        maxDistanceZ,
        chunk_size=1000000,
    )
    nc = len(coincidences["GlobalTime1"])
    print(f"There are {nc} coincidences for policy", policy)

    # save to file
    # WARNING root version >= 5.2.2 needed
    output_file = uproot.recreate(paths.output / f"output_{policy}.root")
    output_file["coincidences"] = coincidences
    output_file["singles"] = copy_tree_for_dump(singles_tree)
    # Compare with reference output
    ref_folder = paths.output_ref

    ref_filename = ref_folder / f"{policy}_Gate9.4.root"
    # print(ref_filename)
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
    tolerance_posX = 0.8
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

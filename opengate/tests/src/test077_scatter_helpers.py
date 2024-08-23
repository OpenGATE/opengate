#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot
import numpy as np


def check_scatter(root_filename):
    root_file = uproot.open(root_filename)
    phsp1 = root_file["phsp"]
    phsp_scatter = root_file["phsp_scatter"]
    phsp_no_scatter = root_file["phsp_no_scatter"]

    print(f"Number of entries in phsp = {phsp1.num_entries}")
    print(f"Number of entries in scatter filtered phsp = {phsp_scatter.num_entries}")
    print(
        f"Number of entries in no_scatter filtered phsp = {phsp_no_scatter.num_entries}"
    )

    scatter_flag = phsp1["ScatterFlag"].array()
    scatter_flag2 = phsp_scatter["ScatterFlag"].array()
    scatter_flag3 = phsp_no_scatter["ScatterFlag"].array()

    # Count the entries where ScatterFlag is 1 or -1
    n_scatter = np.sum(scatter_flag == 1)
    n_no_scatter = np.sum(scatter_flag == 0)

    print(f"phsp1,   nb flag == 0  -> {np.sum(scatter_flag == 0)}")
    print(f"phsp1,   nb flag == 1  -> {np.sum(scatter_flag == 1)}")
    print(f"phsp1,   nb flag == -1 -> {np.sum(scatter_flag == -1)}")
    print()

    print(f"phsp_s,  nb flag == 0  -> {np.sum(scatter_flag2 == 0)}")
    print(f"phsp_s,  nb flag == 1  -> {np.sum(scatter_flag2 == 1)}")
    print(f"phsp_s,  nb flag == -1 -> {np.sum(scatter_flag2 == -1)}")
    print()

    print(f"phsp_ns, nb flag == 0  -> {np.sum(scatter_flag3 == 0)}")
    print(f"phsp_ns, nb flag == 1  -> {np.sum(scatter_flag3 == 1)}")
    print(f"phsp_ns, nb flag == -1 -> {np.sum(scatter_flag3 == -1)}")
    print()

    # check
    b1 = n_scatter == phsp_scatter.num_entries
    utility.print_test(
        b1,
        f"Number of scatter flag is {n_scatter} and "
        f"filtered = {phsp_scatter.num_entries}",
    )

    b2 = n_no_scatter == phsp_no_scatter.num_entries
    utility.print_test(
        b2,
        f"Number of no_scatter flag is {n_no_scatter} and "
        f"filtered = {phsp_no_scatter.num_entries} entries",
    )

    b3 = phsp_scatter.num_entries == np.sum(scatter_flag2 == 1)
    utility.print_test(
        b3,
        f"Check nb filter {phsp_scatter.num_entries} vs {np.sum(scatter_flag2 == 1)}",
    )

    b4 = phsp_no_scatter.num_entries == np.sum(scatter_flag3 != 1)
    utility.print_test(
        b4,
        f"Check nb filter {phsp_no_scatter.num_entries} vs {np.sum(scatter_flag3 != 1)}",
    )

    return b1 and b2 and b3 and b4

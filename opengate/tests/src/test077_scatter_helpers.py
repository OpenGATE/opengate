#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

    scatter_flag = phsp1["UnscatteredPrimaryFlag"].array()
    scatter_flag2 = phsp_scatter["UnscatteredPrimaryFlag"].array()
    scatter_flag3 = phsp_no_scatter["UnscatteredPrimaryFlag"].array()

    # Count the entries where UnscatteredPrimaryFlag is 1 or -1
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
    # tol = 0.01
    # r = np.abs(n_scatter - phsp_scatter.num_entries) / n_scatter
    b1 = n_scatter == phsp_scatter.num_entries
    utility.print_test(
        b1,
        f"Number of scatter flag is {n_scatter} and "
        f"filtered = {phsp_scatter.num_entries} entries",
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

    ####
    phsp1_particles = {}
    phsp2_particles = {}
    print(phsp1.keys())
    for particle in phsp1.arrays():
        if particle["UnscatteredPrimaryFlag"] != 1:
            continue
        key = (particle["EventID"], particle["TrackID"])
        phsp1_particles[key] = particle

    for particle in phsp_scatter.arrays():
        key = (particle["EventID"], particle["TrackID"])
        phsp2_particles[key] = particle

    unique_in_phsp1 = set(phsp1_particles.keys()) - set(phsp2_particles.keys())
    unique_in_phsp2 = set(phsp2_particles.keys()) - set(phsp1_particles.keys())

    print("Particles in phsp1 but not in phsp2:")
    i = 0
    for key in unique_in_phsp1:
        print(phsp1_particles[key])
        i += 1
    print(i)

    print("\nParticles in phsp2 but not in phsp1:")
    i = 0
    for key in unique_in_phsp2:
        p = phsp2_particles[key]
        print(
            p,
            p["EventID"],
            p["TrackID"],
            p["ParentID"],
            p["PreDirection_X"],
            p["PreDirection_Y"],
            p["PreDirection_Z"],
            p["UnscatteredPrimaryFlag"],
            p["KineticEnergy"],
        )
        i += 1
    print(i)

    return b1 and b2 and b3 and b4

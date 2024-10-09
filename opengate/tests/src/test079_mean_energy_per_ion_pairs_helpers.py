#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import numpy as np
from collections import defaultdict
from scipy.optimize import curve_fit


def calculate_angle(dir1, dir2):
    # Calculate the dot product
    dot_product = np.dot(dir1, dir2)

    # Calculate magnitudes
    magnitude1 = np.linalg.norm(dir1)
    magnitude2 = np.linalg.norm(dir2)

    # Calculate the angle between the directions
    cos_theta = dot_product / (magnitude1 * magnitude2)
    return np.arccos(np.clip(cos_theta, -1.0, 1.0))  # Clip to avoid numerical errors


def read_gamma_pairs(root_filename):
    # Load the ROOT file
    file = uproot.open(root_filename)

    # Access the tree
    tree = file["phsp"]

    # Extract relevant branches
    event_id = tree["EventID"].array(library="np")
    particle_name = tree["ParticleName"].array(library="np")
    creator_process = tree["TrackCreatorProcess"].array(library="np")

    # Extract PreDirection components
    pre_dir_x = tree["PreDirection_X"].array(library="np")
    pre_dir_y = tree["PreDirection_Y"].array(library="np")
    pre_dir_z = tree["PreDirection_Z"].array(library="np")

    # Combine components into a single 3D vector for PreDirection
    pre_dir = np.vstack((pre_dir_x, pre_dir_y, pre_dir_z)).T

    # Filter for gamma particles created by the annihilation process
    gamma_mask = (particle_name == "gamma") & (creator_process == "annihil")

    # Dictionary to store paired gammas by EventID
    event_id = event_id[gamma_mask]
    pre_dir = pre_dir[gamma_mask]
    event_dict = defaultdict(list)

    # Grouping gamma particles by EventID
    for i, eid in enumerate(event_id):
        event_dict[eid].append(pre_dir[i])

    # Filter out events with exactly 2 gammas
    gamma_pairs = [dirs for dirs in event_dict.values() if len(dirs) == 2]

    return gamma_pairs


def compute_acollinearity_angles(gamma_pairs):
    acollinearity_angles = []

    for pair in gamma_pairs:
        dir1, dir2 = pair
        angle = calculate_angle(dir1, dir2)
        acollinearity = np.abs(
            np.pi - angle
        )  # Acollinearity deviation from 180 degrees
        acollinearity_angles.append(np.degrees(acollinearity))  # Convert to degrees
        if np.degrees(acollinearity) > 20:
            print(
                f"dir1 = {dir1}, dir2 = {dir2} -> angle = {np.degrees(acollinearity)} {np.degrees(angle)}"
            )

    return acollinearity_angles


def rayleigh(abs_value, amp, scale):
    return amp * (abs_value / scale**2) * np.exp(-((abs_value) ** 2) / (2.0 * scale**2))


def fit_rayleigh(hist_data):
    hist_pos = hist_data[1][:-1] + np.diff(hist_data[1])[0]
    init_param = [1.0, 0.5 / 2.355]
    popt, _ = curve_fit(rayleigh, hist_pos, hist_data[0], p0=init_param)

    return popt[0], popt[1]

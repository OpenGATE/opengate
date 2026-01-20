#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import opengate as gate
import numpy as np
from collections import defaultdict
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

#########################################################################################
# Constants
#########################################################################################
# Units
m = gate.g4_units.m
cm = gate.g4_units.cm
mm = gate.g4_units.mm
eV = gate.g4_units.eV
MeV = gate.g4_units.MeV
Bq = gate.g4_units.Bq
gcm3 = gate.g4_units.g_cm3
deg = gate.g4_units.deg


#########################################################################################
# Recurring elements of the tests in terms of simulation
#########################################################################################
def setup_simulation_engine(path):
    # create simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 12345654
    sim.progress_bar = True

    # add a material database
    sim.volume_manager.add_material_database(path.data / "GateMaterials.db")

    # set the world size
    sim.world.size = [3 * m, 3 * m, 3 * m]
    sim.world.material = "G4_AIR"

    # set the physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("waterbox", "gamma", 10 * mm)
    sim.physics_manager.enable_decay = True

    return sim


def setup_actor(sim, actor_name, volume_name):
    # add phase actor
    curr_actor = sim.add_actor("PhaseSpaceActor", actor_name)
    curr_actor.attached_to = volume_name
    curr_actor.attributes = [
        "EventID",
        "TrackID",
        "PrePosition",
        "PreDirection",
        "PostDirection",
        "ParticleName",
        "TrackCreatorProcess",
        "KineticEnergy",
    ]
    curr_actor.steps_to_store = "first"
    f = sim.add_filter("ParticleFilter", f"f_{actor_name}")
    f.particle = "gamma"
    curr_actor.filters.append(f)

    return curr_actor


#########################################################################################
# Methods used to ascertain the test behavior
#########################################################################################
def calculate_angle(dir1, dir2):
    # Calculate the dot product
    dot_product = np.dot(dir1, dir2)

    # Calculate magnitudes
    magnitude1 = np.linalg.norm(dir1)
    magnitude2 = np.linalg.norm(dir2)

    # Calculate the angle between the directions
    # cos_theta = dot_product / (magnitude1 * magnitude2)
    cos_theta = np.divide(
        dot_product,
        (magnitude1 * magnitude2),
        out=np.zeros_like(dot_product),
        where=(magnitude1 * magnitude2) != 0,
    )
    return np.arccos(np.clip(cos_theta, -1.0, 1.0))  # Clip to avoid numerical errors


def read_gamma_pairs(root_filename, actor_name="phsp", is_btb=False):
    # Load the ROOT file
    file = uproot.open(root_filename)

    # Access the tree
    tree = file[actor_name]

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

    if is_btb:
        gamma_mask = particle_name == "gamma"
    else:
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


def plot_colin_case(acollinearity_angles):
    colin_median = np.median(acollinearity_angles)
    print(
        f"median angle: {colin_median}  min={np.min(acollinearity_angles)}   max={np.max(acollinearity_angles)}"
    )

    plt.hist(
        acollinearity_angles,
        bins=71,
        range=(0, 1.0),
        alpha=0.7,
        color="blue",
        label="Default",
    )

    return colin_median


def plot_acolin_case_mepip(ion_pair_mean_energy, acollinearity_angles, is_second=False):
    label = f"With mean energy per Ion par of {ion_pair_mean_energy / eV:.1f} eV"
    scale = plot_acolin_case(label, acollinearity_angles, is_second)

    return scale


def plot_acolin_case_angle(acolin_FWHM, acollinearity_angles, is_second=False):
    label = f"Acolin. set at {acolin_FWHM / deg:.2f} deg FWHM"
    scale = plot_acolin_case(label, acollinearity_angles, is_second)

    return scale


def plot_acolin_case(label, acollinearity_angles, is_second=False):
    # If two cases of acolin is shown on the same figure, make sure that we can tell
    # them apart
    if is_second:
        hist_color = "brown"
    else:
        hist_color = "red"

    # Range of 0.0 to 1.0 is enforced since in some rare instances, acolinearity is
    # very large, which skew the histogram.
    data = plt.hist(
        acollinearity_angles,
        bins=71,
        range=(0, 1.0),
        alpha=0.7,
        color=hist_color,
        label=label,
    )

    if is_second:
        box_pos = 0.5 * max(data[0])
        fit_color = "c"
    else:
        plt.ylim((0.0, 2.0 * max(data[0])))
        plt.xlim((0.0, 1.0))
        plt.xlabel("Acollinearity Angle (Degrees)")
        plt.ylabel("Counts")
        plt.title("Acollinearity Distribution of Gamma Pairs")
        plt.grid(True)
        box_pos = max(data[0])
        fit_color = "g"
    plt.legend()

    amplitude, scale = fit_rayleigh(data)
    # Negative value change nothing for the fit but it should be positive.
    scale = np.abs(scale)
    x_value = np.linspace(0.0, 1.0, 50)
    # The norm of a isotropic 2D Gaussian centered at [0.0 0.0] is a Rayleigh
    # distribution with a scale equal to the sigme of the 2D Gaussian.
    plt.plot(x_value, rayleigh(x_value, amplitude, scale), fit_color, linewidth=3)

    textstr = f"FWHM = {2.355 * scale:.2f}°\n$\\sigma$ = {scale:.2f}°"
    props = dict(
        boxstyle="round",
        facecolor="wheat",
        edgecolor=fit_color,
        linewidth=3,
        alpha=0.95,
    )

    plt.text(0.7, box_pos, textstr, bbox=props)

    print(label)
    print(textstr)

    return scale

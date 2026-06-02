#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

import numpy as np
import uproot
import matplotlib.pyplot as plt

# Units
MeV = gate.g4_units.MeV
keV = gate.g4_units.keV
Bq = gate.g4_units.Bq
deg = gate.g4_units.deg
mm = gate.g4_units.mm
m = gate.g4_units.m
cm = gate.g4_units.cm
ns = gate.g4_units.ns

PROMPT_PHOTON_KINETIC_ENERGY_MEV = 1.244
MEAN_LIFETIME_NS = 10
SPEED_OF_LIGHT_MM_PER_NS = 299.79246


def propagation_time(hit_position, source_position):
    distance_cm = np.sqrt((hit_position[0] - source_position[0])**2 +
                          (hit_position[1] - source_position[1])**2 +
                          (hit_position[2] - source_position[2])**2)
    return distance_cm / SPEED_OF_LIGHT_MM_PER_NS


def emission_time(hit_time, propagation_time):
    return hit_time - propagation_time


def lifetime(emission_time_annihilation, emission_time_prompt):
    return emission_time_annihilation - emission_time_prompt


def calculate_lifetime(prompt_photon, annihilation_photon, source_position):
    annihilation_hit_position = [
        annihilation_photon["Position_X"], annihilation_photon["Position_Y"],
        annihilation_photon["Position_Z"]
    ]
    prompt_hit_position = [
        prompt_photon["Position_X"], prompt_photon["Position_Y"],
        prompt_photon["Position_Z"]
    ]
    propagation_time_annihilation = propagation_time(annihilation_hit_position,
                                                     source_position)
    propagation_time_prompt = propagation_time(prompt_hit_position,
                                               source_position)
    emission_time_annihilation = emission_time(
        annihilation_photon["GlobalTime"], propagation_time_annihilation)
    emission_time_prompt = emission_time(prompt_photon["GlobalTime"],
                                         propagation_time_prompt)
    return lifetime(emission_time_annihilation, emission_time_prompt)


def calculate_lifetimes(group):
    annihilation_photon = group.iloc[0]
    prompt_photon = group.iloc[3]
    assert np.isclose(prompt_photon["KineticEnergy"],
                      PROMPT_PHOTON_KINETIC_ENERGY_MEV)
    source_position = [
        annihilation_photon["EventPosition_X"],
        annihilation_photon["EventPosition_Y"],
        annihilation_photon["EventPosition_Z"]
    ]
    return calculate_lifetime(prompt_photon, annihilation_photon,
                              source_position)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__,
        "gate_test089_positronium_statistics",
        output_folder="test089")
    print("Starting")

    # create the simulation
    sim = gate.Simulation()
    sim.physics_manager.physics_list_name = 'G4EmLivermorePolarizedPhysics'

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.number_of_threads = 1
    sim.output_dir = paths.output
    sim.random_seed = 1234

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [1. * m, 1. * m, 1. * m]

    # test sources
    source = sim.add_source("PositroniumSource", "source")
    source.n = 1000
    source.position.type = "sphere"
    source.position.radius = 1. * cm

    source.positronium_fractions = [1.]
    source.positronium_lifetimes = [MEAN_LIFETIME_NS * ns]
    source.decay_kinds = ["k3Gamma"]
    source.prompt_photon_probabilities = [1.]
    source.prompt_photon_energies = [PROMPT_PHOTON_KINETIC_ENERGY_MEV * MeV]
    source.mean_positron_range = [0. * mm]
    source.electron_capture_probabilities = [0.]

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # PhaseSpace Actor
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attributes = [
        "EventID", "Position", "KineticEnergy", "GlobalTime", "EventPosition"
    ]
    phsp.debug = True
    phsp.steps_to_store = "first"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    phsp.filters.append(f)
    phsp.output_filename = "output_positronium.root"

    # start simulation
    sim.run()

    # get results
    print(stats)

    phsp_output = uproot.open(phsp.get_output_path())
    df = phsp_output["PhaseSpace"].arrays(library="pd")

    lifetimes = df.groupby('EventID').apply(calculate_lifetimes).reset_index(
        name='lifetime')["lifetime"]

    mean_lifetime = lifetimes.mean()

    plt.figure()
    plt.hist(lifetimes, bins=100)
    plt.yscale("log")
    plt.savefig(paths.output / "lifetime.pdf")

    print("Mean lifetime: " + str(mean_lifetime))

    assert np.isclose(mean_lifetime, MEAN_LIFETIME_NS, atol=0., rtol=.1)

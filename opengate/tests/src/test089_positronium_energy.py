#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot
import matplotlib.pyplot as plt
import numpy as np
import scipy

# Units
MeV = gate.g4_units.MeV
keV = gate.g4_units.keV
Bq = gate.g4_units.Bq
deg = gate.g4_units.deg
mm = gate.g4_units.mm
m = gate.g4_units.m
cm = gate.g4_units.cm
ns = gate.g4_units.ns


def one_photon_energy(en):
    m = 1
    first_term = en * (m - en) / (2 * m - en)**2
    second_term = (2 * m - en) / en
    third_term = ((2 * m * (m - en) / (en * en) - 2 * m * (m - en)**2 /
                   (2 * m - en)**3)) * np.log((m - en) / m)
    return first_term + second_term + third_term


def normalize_energies(en):
    MeVToKeV = 1e3
    return en * MeVToKeV / 511


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__,
                                           "gate_test089_positronium_energy",
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
    world.size = [2 * m, 2 * m, 2 * m]

    # parameters

    # test sources
    source = sim.add_source("PositroniumSource", "source")
    source.position.type = "sphere"
    source.position.radius = 1 * mm
    source.n = 10_000

    source.positronium_fractions = [1.]
    source.positronium_lifetimes = [0.122 * ns]
    source.decay_kinds = ["k3Gamma"]
    source.prompt_photon_probabilities = [0.]
    source.prompt_photon_energies = [1.244 * MeV]

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # PhaseSpace Actor
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attributes = ["KineticEnergy"]
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

    # check energy distribution

    nbins = 100

    phsp_output = uproot.open(phsp.get_output_path())
    df = phsp_output["PhaseSpace"].arrays(library="pd")
    counts, bins = np.histogram(normalize_energies(df["KineticEnergy"]), nbins)
    counts = counts / np.max(counts)

    xs = np.linspace(0.0001, 0.9999, nbins)
    expected_distribution = one_photon_energy(xs)

    plt.figure()
    plt.stairs(counts, bins)
    plt.plot(xs, expected_distribution)
    plt.savefig(paths.output / "distribution.pdf")

    ks = scipy.stats.kstest(counts, expected_distribution)
    is_ok = ks.pvalue > .95

    utility.test_ok(is_ok)

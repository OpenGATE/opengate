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

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__,
                                           "gate_test089_decay_index",
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

    nchannels = 10
    source.channels_from_fractions.fractions = [.1] * nchannels
    source.channels_from_fractions.decay_kinds = ["k3Gamma"] * nchannels
    source.positronium_lifetimes = [0.122 * ns] * nchannels
    source.prompt_gamma_probabilities = [0.] * nchannels
    source.prompt_gamma_energies = [1.244 * MeV] * nchannels

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # PhaseSpace Actor
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attributes = ["PositroniumDecayIndex"]
    phsp.debug = True
    phsp.steps_to_store = "first"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    phsp.filters.append(f)
    phsp.output_filename = "output_positronium_decay_index.root"

    # start simulation
    sim.run()

    # get results
    print(stats)

    # check energy distribution

    phsp_output = uproot.open(phsp.get_output_path())
    df = phsp_output["PhaseSpace"].arrays(library="pd")

    plt.figure()
    plt.hist(df["PositroniumDecayIndex"], bins=nchannels)
    plt.savefig(paths.output / "decay_index.pdf")

    is_ok = np.isclose(df["PositroniumDecayIndex"].mean(), (nchannels - 1) / 2,
                       rtol=0.,
                       atol=.1)
    utility.test_ok(is_ok)

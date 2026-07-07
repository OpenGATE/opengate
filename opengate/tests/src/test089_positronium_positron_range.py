#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

import uproot
import numpy as np
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

MEAN_POSITRON_RANGE_MM = 10

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__,
                                           "gate_test089_positronium_range",
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
    source.position.type = "point"

    source.channels_from_fractions.fractions = [1.]
    source.channels_from_fractions.decay_kinds = ["k3Gamma"]
    source.positronium_lifetimes = [100. * ns]
    source.prompt_gamma_probabilities = [0.]
    source.prompt_gamma_energies = [1. * MeV]
    source.mean_positron_range = [MEAN_POSITRON_RANGE_MM * mm]

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # PhaseSpace Actor
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attributes = ["PrePosition"]
    phsp.steps_to_store = "first"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    phsp.filters.append(f)
    phsp.output_filename = "output_positronium_positron_range.root"

    # start simulation
    sim.run()

    # get results
    print(stats)

    phsp_output = uproot.open(phsp.get_output_path())
    df = phsp_output["PhaseSpace"].arrays(library="pd")

    source_position = source.position.translation
    position_x = df["PrePosition_X"]
    position_y = df["PrePosition_Y"]
    position_z = df["PrePosition_Z"]
    r = np.sqrt((position_x - source_position[0])**2 +
                (position_y - source_position[1])**2 +
                (position_z - source_position[2])**2)
    sigma = r.mean() / np.sqrt(8. / np.pi)

    fig, (fig_x, fig_y, fig_z) = plt.subplots(nrows=1, ncols=3)
    nbins = 50
    fig_x.hist(position_x, bins=nbins)
    fig_x.set_title('$x$')
    fig_y.hist(position_y, bins=nbins)
    fig_y.set_title('$y$')
    fig_z.hist(position_z, bins=nbins)
    fig_z.set_title('$z$')
    plt.savefig(paths.output / "positron_range.pdf")

    is_ok = np.isclose(r.mean(), MEAN_POSITRON_RANGE_MM, atol=.5, rtol=0.)
    is_ok = is_ok and np.isclose(position_x.std(), sigma, atol=.5, rtol=0.)
    is_ok = is_ok and np.isclose(position_y.std(), sigma, atol=.5, rtol=0.)
    is_ok = is_ok and np.isclose(position_z.std(), sigma, atol=.5, rtol=0.)

    utility.test_ok(is_ok)

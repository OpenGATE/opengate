#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import math

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
    world.size = [2 * m, 2 * m, 2 * m]

    # parameters
    n = 1000
    twoGammasRatio = .5
    threeGammasRatio = .5
    twoGammasPromptProbability = 0.
    threeGammasPromptProbability = 1.

    # test sources
    source = sim.add_source("PositroniumSource", "source")
    source.n = 1000
    source.position.type = "sphere"
    source.position.radius = 20 * cm

    source.positronium_fractions = [twoGammasRatio, threeGammasRatio]
    source.positronium_lifetimes = [0.122 * ns, 0.122 * ns]
    source.decay_kinds = ["k2Gamma", "k3Gamma"]
    source.prompt_photon_probabilities = [
        twoGammasPromptProbability, threeGammasPromptProbability
    ]
    source.prompt_photon_energies = [1.244 * MeV, 1.244 * MeV]
    source.mean_positron_range = [0. * mm, 0. * mm]
    source.electron_capture_probabilities = [0., 0.]

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # get results
    print(stats)

    # check expected number of gammas
    expected_number_of_gammas = (n * twoGammasRatio *
                                 (2 + twoGammasPromptProbability)) + (
                                     n * threeGammasRatio *
                                     (3 + threeGammasPromptProbability))
    is_ok = math.isclose(stats.user_output.stats.merged_data.track_types.gamma,
                         expected_number_of_gammas,
                         rel_tol=0.,
                         abs_tol=100.)
    utility.test_ok(is_ok)

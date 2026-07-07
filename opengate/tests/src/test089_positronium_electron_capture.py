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
        "gate_test089_positronium_electron_capture",
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

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # parameters
    n = 1000
    gammasPromptProbability = 1.
    electronCaptureProbability = .25

    # test sources
    source = sim.add_source("PositroniumSource", "source")
    source.n = n
    source.position.type = "sphere"
    source.position.radius = 20 * cm

    source.channels_from_fractions.fractions = [1.]
    source.channels_from_fractions.decay_kinds = ["k2Gamma"]
    source.positronium_lifetimes = [0.122 * ns]
    source.prompt_gamma_probabilities = [gammasPromptProbability]
    source.prompt_gamma_energies = [1.244 * MeV]
    source.electron_capture_probabilities = [electronCaptureProbability]

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # get results
    print(stats)

    # check expected number of gammas
    expected_number_of_gammas = n * 2. * (
        1. - electronCaptureProbability) + n * gammasPromptProbability
    is_ok = math.isclose(stats.user_output.stats.merged_data.track_types.gamma,
                         expected_number_of_gammas,
                         rel_tol=0.,
                         abs_tol=100.)
    utility.test_ok(is_ok)

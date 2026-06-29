#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4
from opengate.tests import utility
from opengate.sources.positroniumsources import PositroniumSource

import numpy as np


def test_channel(source, index, positron_interaction, decay_kind,
                 positronium_lifetime, prompt_gamma_probability,
                 prompt_gamma_energy):
    if source.channels_from_intensities.positron_interactions[
            index] != positron_interaction:
        return False
    if source.channels_from_fractions.decay_kinds[index] != decay_kind:
        return False
    if source.positronium_lifetimes[index] != positronium_lifetime:
        return False
    if source.prompt_gamma_probabilities[index] != prompt_gamma_probability:
        return False
    if source.prompt_gamma_energies[index] != prompt_gamma_energy:
        return False
    return True


def test_calculate_fractions_from_lifetimes():
    intensities = [12, 4, 2, 2]
    positronium_lifetimes = [.4, 2., .125, 50.]
    prompt_gamma_probabilities = [5, 6, 7, 8]
    prompt_gamma_energies = [1., 2., 3., 4.]
    positron_interactions = ["kDirect", "kOrthoPs", "kParaPs", "kOrthoPs"]

    # create the simulation
    sim = gate.Simulation()

    # test sources
    source = sim.add_source("PositroniumSource", "source")
    source.n = 100
    source.channels_from_intensities.intensities = intensities
    source.positronium_lifetimes = positronium_lifetimes
    source.prompt_gamma_probabilities = prompt_gamma_probabilities
    source.prompt_gamma_energies = prompt_gamma_energies
    source.channels_from_intensities.positron_interactions = positron_interactions

    sim.run()

    is_ok = True

    is_ok = is_ok and test_channel(
        source, 0, "kDirect", "k2Gamma", positronium_lifetimes[0],
        prompt_gamma_probabilities[0], prompt_gamma_energies[0])
    is_ok = is_ok and test_channel(
        source, 1, "kDirect", "k3Gamma", positronium_lifetimes[0],
        prompt_gamma_probabilities[0], prompt_gamma_energies[0])
    is_ok = is_ok and test_channel(
        source, 2, "kOrthoPs", "k2Gamma", positronium_lifetimes[1],
        prompt_gamma_probabilities[1], prompt_gamma_energies[1])
    is_ok = is_ok and test_channel(
        source, 3, "kOrthoPs", "k3Gamma", positronium_lifetimes[1],
        prompt_gamma_probabilities[1], prompt_gamma_energies[1])
    is_ok = is_ok and test_channel(
        source, 4, "kOrthoPs", "k2Gamma", positronium_lifetimes[3],
        prompt_gamma_probabilities[3], prompt_gamma_energies[3])
    is_ok = is_ok and test_channel(
        source, 5, "kOrthoPs", "k3Gamma", positronium_lifetimes[3],
        prompt_gamma_probabilities[3], prompt_gamma_energies[3])
    is_ok = is_ok and test_channel(
        source, 6, "kParaPs", "k2Gamma", positronium_lifetimes[2],
        prompt_gamma_probabilities[2], prompt_gamma_energies[2])

    good_fractions = [
        371. / 620., 1. / 620., 14. / 71., 1. / 355., 23. / 355., 5. / 142.,
        0.1
    ]
    is_ok = is_ok and np.all(
        np.isclose(source.channels_from_fractions.fractions, good_fractions))

    return is_ok


def test_normalize_fractions():
    fractions = [12, 2, 4, 2]
    good_fractions = [.6, .1, .2, .1]
    output_fractions = PositroniumSource.normalize_fractions(fractions)
    is_ok = np.all(np.isclose(output_fractions, good_fractions))
    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__,
                                           "gate_test089_positronium_helper",
                                           output_folder="test089")

    is_ok = True

    is_ok = is_ok and test_calculate_fractions_from_lifetimes()
    is_ok = is_ok and test_normalize_fractions()

    utility.test_ok(is_ok)

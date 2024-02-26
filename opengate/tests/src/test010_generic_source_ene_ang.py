#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import gatetools

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder=None, output_folder="test010"
    )

    print(paths.output_ref)

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    deg = gate.g4_units.deg
    um = gate.g4_units.um
    keV = gate.g4_units.keV
    g_cm3 = gate.g4_units.g_cm3

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.number_of_threads = 1
    # sim.random_seed = 123654 # FIXME set a fixed value for the final test

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    # test sources
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.n = 1e6 / sim.number_of_threads
    source.n = 1e5 / sim.number_of_threads
    source.position.type = "point"
    source.position.translation = [0 * cm, 0 * cm, 0 * cm]
    source.direction.type = "histogram"
    source.direction.histogram_theta_weight = [0, 0.2, 0.6, 0.3, 0.05]
    source.direction.histogram_theta_angle = [
        20 * deg,
        45 * deg,
        90 * deg,
        110 * deg,
        120 * deg,
    ]
    source.direction.histogram_phi_weight = [0, 1]
    source.direction.histogram_phi_angle = [0 * deg, 360 * deg]
    source.energy.type = "histogram"
    source.energy.histogram_weight = [0, 0.2, 0.3, 0.3, 1]
    source.energy.histogram_energy = [30 * keV, 40 * keV, 70 * keV, 80 * keV, 100 * keV]

    """
    Weights and energies are given as pairs of (weight, energy) to Geant4.
    Geant4 documentation :
    "Currently histograms are limited to 1024 bins. The first value of each user input data pair is treated as the upper
    edge of the histogram bin and the second value is the bin content. The exception is the very first data pair the
    user input whose first value is the treated as the lower edge of the first bin of the histogram, and the second
    value is not used. This rule applies to all distribution histograms, as well as histograms for biasing."
    """

    # stats
    stats_actor = sim.add_actor("SimulationStatisticsActor", "stats")

    # phsp
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.output = paths.output / "test010-ene-angles.root"
    phsp.mother = "world"
    phsp.attributes = ["EventKineticEnergy", "EventDirection", "KineticEnergy"]

    # start simulation
    sim.run()

    # get results
    stats = sim.output.get_actor("stats")
    print(stats)
    print(phsp.output)

    # FIXME : do the test
    utility.test_ok(False)

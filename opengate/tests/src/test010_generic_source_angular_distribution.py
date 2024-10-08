#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import pathlib


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test010")
    ref_path = paths.output_ref

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
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
    sim.visu = False
    sim.visu_type = "vrml"
    sim.number_of_threads = 1
    sim.random_seed = 123654
    sim.output_dir = paths.output

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    # set daughter volume for doseactor
    image_volume = sim.add_volume("Box", "image_volume")
    image_volume.material = "G4_Pb"
    image_volume.mother = "world"
    image_volume.size = [100 * cm, 1 * cm, 100 * cm]
    image_volume.translation = [0, -50 * cm, 0]

    # test sources
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    # source.n = 100 / sim.number_of_threads
    source.n = 1e6 / sim.number_of_threads
    source.position.type = "point"
    source.position.translation = [0 * cm, 0 * cm, 0 * cm]
    source.direction.type = "histogram"
    # Put zero as first value of weight
    source.direction.histogram_theta_weight = [0, 1]
    source.direction.histogram_theta_angle = [80 * deg, 100 * deg]
    source.direction.histogram_phi_weight = [0, 0.3, 0.5, 1, 0.5, 0.3]
    source.direction.histogram_phi_angle = [
        60 * deg,
        70 * deg,
        80 * deg,
        100 * deg,
        110 * deg,
        120 * deg,
    ]
    source.energy.type = "gauss"
    source.energy.mono = 70 * keV

    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test010-generic_source_angular_distribution.mhd"
    dose.edep_uncertainty.active = True
    dose.attached_to = "image_volume"
    dose.size = [100, 1, 100]
    dose.spacing = [10 * mm, 1 * cm, 10 * mm]

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True

    # start simulation
    sim.run()

    # get results
    print(stat)
    print(dose)

    # tests
    stats_ref = utility.read_stat_file(
        ref_path / "test010_generic_source_angular_distribution_stats_ref.txt"
    )
    is_ok = utility.assert_stats(stat, stats_ref, 0.11)

    print("\nDifference for EDEP")
    is_ok = (
        utility.assert_images(
            ref_path / "test010-generic_source_angular_distribution_edep_ref.mhd",
            dose.edep.get_output_path(),
            stat,
            tolerance=13,
            ignore_value=0,
            sum_tolerance=1,
        )
        and is_ok
    )

    print("\nDifference for uncertainty")
    is_ok = (
        utility.assert_images(
            ref_path
            / "test010-generic_source_angular_distribution_edep_uncertainty_ref.mhd",
            dose.edep_uncertainty.get_output_path(),
            stat,
            tolerance=30,
            ignore_value=1,
            sum_tolerance=1,
        )
        and is_ok
    )

    utility.test_ok(is_ok)

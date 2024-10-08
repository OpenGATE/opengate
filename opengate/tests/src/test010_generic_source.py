#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test010_generic_source", output_folder="test010"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    # useful units
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    deg = gate.g4_units.deg
    mm = gate.g4_units.mm
    m = gate.g4_units.m
    cm = gate.g4_units.cm

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # add a simple volume
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
    waterbox.material = "G4_WATER"

    # test sources
    source = sim.add_source("GenericSource", "source1")
    source.particle = "gamma"
    source.activity = 10000 * Bq / sim.number_of_threads
    source.position.type = "sphere"
    source.position.radius = 5 * mm
    source.position.translation = [-3 * cm, 30 * cm, -3 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, -1, 0]
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV

    source = sim.add_source("GenericSource", "source2")
    source.particle = "proton"
    source.activity = 10000 * Bq / sim.number_of_threads
    source.position.type = "disc"
    source.position.radius = 5 * mm
    source.position.translation = [6 * cm, 5 * cm, -30 * cm]
    # source.position.rotation = Rotation.from_euler('x', 45, degrees=True).as_matrix()
    source.position.rotation = Rotation.identity().as_matrix()
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.energy.type = "gauss"
    source.energy.mono = 140 * MeV
    source.energy.sigma_gauss = 10 * MeV

    source = sim.add_source("GenericSource", "s3")
    source.particle = "proton"
    source.activity = 10000 * Bq / sim.number_of_threads
    source.position.type = "box"
    source.position.size = [4 * cm, 4 * cm, 4 * cm]
    source.position.translation = [8 * cm, 8 * cm, 30 * cm]
    source.direction.type = "focused"
    source.direction.focus_point = [1 * cm, 2 * cm, 3 * cm]
    source.energy.type = "gauss"
    source.energy.mono = 140 * MeV
    source.energy.sigma_gauss = 10 * MeV

    source = sim.add_source("GenericSource", "s4")
    source.particle = "proton"
    source.activity = 10000 * Bq / sim.number_of_threads
    source.position.type = "box"
    source.position.size = [4 * cm, 4 * cm, 4 * cm]
    source.position.translation = [-3 * cm, -3 * cm, -3 * cm]
    # source.position.rotation = Rotation.from_euler('x', 45, degrees=True).as_matrix()
    source.position.rotation = Rotation.identity().as_matrix()
    source.direction.type = "iso"
    source.energy.type = "gauss"
    source.energy.mono = 80 * MeV
    source.energy.sigma_gauss = 1 * MeV

    # actors
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")

    # src_info = sim.add_actor('SourceInfoActor', 'src_info')
    # src_info.filename = 'output/sources.root'

    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test010.mhd"
    dose.attached_to = waterbox
    dose.size = [50, 50, 50]
    dose.spacing = [4 * mm, 4 * mm, 4 * mm]

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")
    # sim.g4_commands_after_init.append("/run/verbose 2")
    # sim.g4_commands_after_init.append("/event/verbose 2")
    # sim.g4_commands_after_init.append("/tracking/verbose 1")

    # start simulation
    sim.run()

    # print
    print("Simulation seed:", sim.current_random_seed)

    # get results
    print(stats_actor)
    print(dose)

    # gate_test10
    # Gate mac/main.mac
    # Current version is two times slower :(
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    print("-" * 80)
    is_ok = utility.assert_stats(stats_actor, stats_ref, tolerance=0.05)
    is_ok = is_ok and utility.assert_images(
        paths.gate_output / "output-Edep.mhd",
        dose.edep.get_output_path(),
        stats_actor,
        tolerance=30,
    )

    utility.test_ok(is_ok)

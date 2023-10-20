#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test010_generic_source")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.number_of_threads = 1

    # set the world size like in the Gate macro
    m = gate.g4_units.m
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # add a simple volume
    waterbox = sim.add_volume("Box", "waterbox")
    cm = gate.g4_units.cm
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
    waterbox.material = "G4_WATER"

    # useful units
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    deg = gate.g4_units.deg
    mm = gate.g4_units.mm

    # test sources
    source = sim.add_source("GenericSource", "source1")
    source.particle = "gamma"
    source.activity = 10000 * Bq / ui.number_of_threads
    source.position.type = "sphere"
    source.position.radius = 5 * mm
    source.position.translation = [-3 * cm, 30 * cm, -3 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, -1, 0]
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV

    source = sim.add_source("GenericSource", "source2")
    source.particle = "proton"
    source.activity = 10000 * Bq / ui.number_of_threads
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
    source.activity = 10000 * Bq / ui.number_of_threads
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
    source.activity = 10000 * Bq / ui.number_of_threads
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
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    # src_info = sim.add_actor('SourceInfoActor', 'src_info')
    # src_info.filename = 'output/sources.root'

    dose = sim.add_actor("DoseActor", "dose")
    dose.output = paths.output / "test010-edep.mhd"
    dose.mother = "waterbox"
    dose.size = [50, 50, 50]
    dose.spacing = [4 * mm, 4 * mm, 4 * mm]

    # verbose
    sim.apply_g4_command("/tracking/verbose 0")
    # sim.apply_g4_command("/run/verbose 2")
    # sim.apply_g4_command("/event/verbose 2")
    # sim.apply_g4_command("/tracking/verbose 1")

    # start simulation
    sim.run()

    # print
    print("Simulation seed:", sim.output.current_random_seed)

    # get results
    stats = sim.output.get_actor("Stats")
    print(stats)

    dose = sim.output.get_actor("dose")
    print(dose)

    # gate_test10
    # Gate mac/main.mac
    # Current version is two times slower :(
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    print("-" * 80)
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.05)
    is_ok = is_ok and utility.assert_images(
        paths.gate_output / "output-Edep.mhd",
        paths.output / "test010-edep.mhd",
        stats,
        tolerance=30,
    )

    utility.test_ok(is_ok)

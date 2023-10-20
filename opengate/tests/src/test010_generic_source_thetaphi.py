#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import gatetools


def root_load_xyz(root_file: str, keys: [str]):
    data_ref, keys_ref, m_ref = gatetools.phsp.load(root_file)

    index_x = keys_ref.index(keys[0])
    index_y = keys_ref.index(keys[1])
    index_z = keys_ref.index(keys[2])

    xs = [data_ref_i[index_x] for data_ref_i in data_ref]
    ys = [data_ref_i[index_y] for data_ref_i in data_ref]
    zs = [data_ref_i[index_z] for data_ref_i in data_ref]

    return xs, ys, zs


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test010_generic_source_thetaphi"
    )

    print(paths.output_ref)

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    deg = gate.g4_units.deg
    um = gate.g4_units.um
    g_cm3 = gate.g4_units.g_cm3

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.number_of_threads = 1

    # materials
    sim.add_material_weights("Vacuum", ["H"], [1], 1e-9 * g_cm3)

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "Vacuum"

    # add a simple volume
    phsp = sim.add_volume("Box", "phsp")
    phsp.size = [40 * cm, 40 * cm, 1 * um]
    phsp.material = "Vacuum"

    # test sources
    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.activity = 1e6 * Bq / ui.number_of_threads
    source.position.type = "point"
    source.position.translation = [0 * cm, 0 * cm, 1 * m]
    source.direction.type = "iso"
    source.direction.theta = [0 * deg, 10 * deg]
    source.direction.phi = [0 * deg, 360 * deg]
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    phspActor = sim.add_actor("PhaseSpaceActor", "phspActor")
    phspActor.output = paths.output / "test010-thetaphi-phsp.root"
    phspActor.mother = "phsp"
    phspActor.attributes = [
        "Position",
    ]

    # verbose
    sim.apply_g4_command("/tracking/verbose 0")

    # start simulation
    sim.run()

    # print
    print("Simulation seed:", sim.output.current_random_seed)

    # get results
    stats = sim.output.get_actor("Stats")
    print(stats)

    # gate_test10_thetaphi
    # Gate mac/main.mac
    # Current version is two times faster (:
    print("-" * 80)

    g9_xs, g9_ys, g9_zs = root_load_xyz(
        paths.output_ref / "test010_thetaphi_phsp.root", ["X", "Y", "Z"]
    )
    g9_xmin, g9_xmax = min(g9_xs), max(g9_xs)
    g9_ymin, g9_ymax = min(g9_ys), max(g9_ys)
    g9_zmin, g9_zmax = min(g9_zs), max(g9_zs)

    g10_xs, g10_ys, g10_zs = root_load_xyz(
        phspActor.output, ["Position_X", "Position_Y", "Position_Z"]
    )
    g10_xmin, g10_xmax = min(g10_xs), max(g10_xs)
    g10_ymin, g10_ymax = min(g10_ys), max(g10_ys)
    g10_zmin, g10_zmax = min(g10_zs), max(g10_zs)

    # Tolerance in mm
    is_ok = True
    is_ok = is_ok and utility.check_diff_abs(
        g9_xmin, g10_xmin, tolerance=0.05, txt="x min"
    )
    is_ok = is_ok and utility.check_diff_abs(
        g9_xmax, g10_xmax, tolerance=0.05, txt="x max"
    )
    is_ok = is_ok and utility.check_diff_abs(
        g9_ymin, g10_ymin, tolerance=0.05, txt="y min"
    )
    is_ok = is_ok and utility.check_diff_abs(
        g9_ymax, g10_ymax, tolerance=0.05, txt="y max"
    )
    is_ok = is_ok and utility.check_diff_abs(
        g9_zmin, g10_zmin, tolerance=1e-2, txt="z min"
    )
    is_ok = is_ok and utility.check_diff_abs(
        g9_zmax, g10_zmax, tolerance=1e-2, txt="z max"
    )

    utility.test_ok(is_ok)

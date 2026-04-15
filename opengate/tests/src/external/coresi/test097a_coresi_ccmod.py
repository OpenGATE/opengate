#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility
from opengate.actors.coincidences import *
import opengate.contrib.compton_camera.macaco as macaco
import opengate.contrib.compton_camera.coresi_helpers as coresi

if __name__ == "__main__":

    # get tests paths
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test097_coresi_ccmod"
    )
    output_folder = paths.output
    data_folder = paths.data

    # units
    m = g4_units.m
    mm = g4_units.mm
    cm = g4_units.cm
    keV = g4_units.keV
    Bq = g4_units.Bq
    MBq = 1e6 * g4_units.Bq
    sec = g4_units.s
    ns = g4_units.ns

    # sim
    sim = gate.Simulation()
    sim.visu = False
    sim.visu_type = "vrml"
    sim.random_seed = "auto"
    sim.output_dir = output_folder
    sim.number_of_threads = 4
    sim.progress_bar = True

    # world
    world = sim.world
    world.size = [0.5 * m, 0.5 * m, 0.7 * m]
    sim.world.material = "G4_AIR"

    # add one camera
    name1 = "macaco1"
    macaco1 = macaco.add_macaco1_camera(sim, name1)
    camera1 = macaco1["camera"]
    scatterer = macaco1["scatterer"]
    absorber = macaco1["absorber"]
    camera1.translation = [0, 0, 10 * cm]

    # add the digitizer (output singles)
    scatt_file, abs_file = macaco.add_macaco1_camera_digitizer(sim, scatterer, absorber)
    print(f"Scatt file: {scatt_file}")
    print(f"Abs file: {abs_file}")

    # stats
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)
    sim.physics_manager.set_production_cut(camera1.name, "all", 0.1 * mm)
    # sim.physics_manager.set_production_cut(camera2.name, "all", 0.1 * mm)

    # source
    source = sim.add_source("GenericSource", "src")
    source.particle = "gamma"
    source.energy.mono = 662 * keV
    source.position.type = "sphere"
    source.position.radius = 0.25 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.activity = 0.847 * MBq / sim.number_of_threads

    # acquisition time
    if sim.visu:
        source.activity = 10 * Bq
    sim.run_timing_intervals = [[0 * sec, 30 * sec]]

    # go
    # sim.run()

    # print stats
    print(stats)

    # compute the coincidences
    print()
    print(f"Computing coincidences from {scatt_file.name} and {abs_file.name}")
    coinc_file = output_folder / "coincidences.root"
    coincidences = macaco.macaco1_compute_coincidences(
        scatt_file,
        abs_file,
        time_windows=12 * ns,
        output_root_filename=coinc_file,
        scatt_tree_name="ThrScatt",
        abs_tree_name="ThrAbs",
        merged_tree_name="Singles",
    )
    root_write_trees(coinc_file, ["Coincidences"], [coincidences])
    print(f"Coincidences file: {coinc_file}")
    print(f"Number of coincidences {len(coincidences)}")

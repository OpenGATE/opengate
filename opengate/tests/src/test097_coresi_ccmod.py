#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.utility import g4_units
import opengate.tests.utility as utility
import opengate.contrib.compton_camera.macaco as macaco
from opengate.actors.coincidences import *

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

    # sim
    sim = gate.Simulation()
    sim.visu = False
    sim.visu_type = "qt"
    sim.random_seed = "auto"
    sim.output_dir = output_folder
    sim.number_of_threads = 1

    # world
    world = sim.world
    world.size = [1 * m, 1 * m, 2 * m]
    sim.world.material = "G4_AIR"

    # add the camera
    camera = macaco.add_macaco1_camera(sim, "macaco1")

    # stats
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"

    # PhaseSpace Actor
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = camera
    phsp.attributes = [
        "TotalEnergyDeposit",
        "PreKineticEnergy",
        "PostKineticEnergy",
        "PostPosition",
        "ProcessDefinedStep",
        "ParticleName",
        "EventID",
        "ParentID",
        "PDGCode",
        "TrackVertexKineticEnergy",
        "GlobalTime",
    ]
    phsp.output_filename = "phsp.root"
    phsp.steps_to_store = "allsteps"

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option2"
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)
    sim.physics_manager.set_production_cut(camera.name, "all", 0.1 * mm)

    # source
    source = sim.add_source("GenericSource", "src")
    source.particle = "gamma"
    source.energy.mono = 662 * keV
    source.position.type = "sphere"
    source.position.radius = 0.25 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.activity = 0.847 * MBq / sim.number_of_threads

    if sim.visu:
        source.activity = 1 * Bq

    sim.run_timing_intervals = [[0 * sec, 5 * sec]]

    # go
    sim.run()

    # print stats
    print(stats)

    # open the root file and create coincidences
    print()
    print(f"Output file: {phsp.get_output_path()}")
    root_file = uproot.open(phsp.get_output_path())
    tree = root_file["PhaseSpace"]
    hits = tree.arrays(library="pd")
    print(f"Number of hits: {len(hits)} ")
    singles = ccmod_ideal_singles(hits)
    print(f"Found: {len(singles)} singles")
    coinc = ccmod_ideal_coincidences(singles)
    print(f"Found: {len(coinc)} coincidences")

    # write the new root with coinc
    filename = str(phsp.get_output_path()).replace(".root", "_coinc.root")
    root_write_trees(
        filename, ["hits", "singles", "coincidences"], [hits, singles, coinc]
    )
    print(f"Output file: {filename}")
    print()

    # CORESI stage1: create the configuration file
    # coresi_config =

    # CORESI stage2: convert the root file

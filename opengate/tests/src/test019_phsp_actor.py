#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
import os

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "", output_folder="test019")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.visu_type = "vrml"
    ui.check_volumes_overlap = False
    ui.number_of_threads = 1
    ui.random_seed = 321654

    # units
    m = gate.g4_units("m")
    mm = gate.g4_units("mm")
    nm = gate.g4_units("nm")
    Bq = gate.g4_units("Bq")
    MeV = gate.g4_units("MeV")

    #  adapt world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_AIR"

    # virtual plane for phase space
    plane = sim.add_volume("Tubs", "phase_space_plane")
    plane.mother = world.name
    plane.material = "G4_AIR"
    plane.rmin = 0
    plane.rmax = 700 * mm
    plane.dz = 1 * nm  # half height
    plane.translation = [0, 0, -100 * mm]
    plane.color = [1, 0, 0, 1]  # red

    # e- source
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.type = "gauss"
    source.energy.mono = 1 * MeV
    source.energy.sigma_gauss = 0.5 * MeV
    source.position.type = "disc"
    source.position.radius = 20 * mm
    source.position.translation = [0, 0, 0 * mm]
    source.direction.type = "momentum"
    source.n = 66

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # PhaseSpace Actor
    ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    ta2.mother = plane.name
    ta2.attributes = [
        "KineticEnergy",
        "PostPosition",
        "PrePosition",
        "PrePositionLocal",
        "ParticleName",
        "PreDirection",
        "PreDirectionLocal",
        "PostDirection",
        "TimeFromBeginOfEvent",
        "GlobalTime",
        "LocalTime",
        "EventPosition",
        "PDGCode",
    ]
    ta2.output = paths.output / "test019_phsp_actor.root"
    ta2.debug = False

    # run the simulation once with no particle in the phsp
    source.direction.momentum = [0, 0, 1]
    ta2.output = paths.output / "test019_phsp_actor_empty.root"
    output = sim.run(start_new_process=True)
    print(output.get_actor("Stats"))

    # check if empty (the root file does not exist)
    phsp = output.get_actor("PhaseSpace")
    is_ok = phsp.fTotalNumberOfEntries == 0
    gate.print_test(is_ok, f"empty phase space = {phsp.fTotalNumberOfEntries}")
    print()

    # redo with the right direction
    source.direction.momentum = [0, 0, -1]
    ta2.output = paths.output / "test019_phsp_actor.root"
    sim.run(start_new_process=True)
    print(output.get_actor("Stats"))

    # check if exists and NOT empty
    hits = uproot.open(ta2.output)["PhaseSpace"]
    is_ok2 = source.n - 10 < hits.num_entries < source.n + 10
    gate.print_test(is_ok2, f"Number of entries = {hits.num_entries} / {source.n}")
    print()

    is_ok = is_ok and is_ok2
    gate.test_ok(is_ok)

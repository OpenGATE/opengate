#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test019")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.output_dir = paths.output
    sim.g4_verbose = False
    sim.visu = False
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.random_seed = 321654
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV

    #  adapt world size
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    # virtual plane for phase space
    plane = sim.add_volume("Tubs", "phase_space_plane")
    plane.mother = sim.world
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
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats_actor.track_types_flag = True

    # PhaseSpace Actor
    ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    ta2.attached_to = plane.name
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
    ta2.debug = False

    # run the simulation once with no particle in the phsp
    source.direction.momentum = [0, 0, 1]
    ta2.output_filename = "test019_phsp_actor_empty.root"

    # run
    sim.run(start_new_process=True)
    print(stats_actor)

    # check if empty (the root file does not exist)
    is_ok = ta2.total_number_of_entries == 0
    utility.print_test(is_ok, f"empty phase space = {ta2.total_number_of_entries}")
    print()

    # redo with the right direction
    source.direction.momentum = [0, 0, -1]
    ta2.output_filename = "test019_phsp_actor.root"
    sim.run(start_new_process=True)
    print(stats_actor)

    # check if exists and NOT empty
    hits = uproot.open(ta2.get_output_path_string())["PhaseSpace"]
    is_ok2 = source.n - 10 < hits.num_entries < source.n + 10
    utility.print_test(is_ok2, f"Number of entries = {hits.num_entries} / {source.n}")
    print()

    is_ok = is_ok and is_ok2
    utility.test_ok(is_ok)

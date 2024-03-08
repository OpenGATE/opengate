#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test072")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.number_of_threads = 1
    # sim.random_seed = 123456

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

    # test sources
    source = sim.add_source("GenericSource", "b2b")
    source.particle = "back_to_back"
    source.n = 100
    source.position.type = "sphere"
    source.position.radius = 5 * mm
    source.direction.type = "iso"
    source.direction.accolinearity_flag = False
    # note : source.energy is ignored (always 511 keV)
    # FIXME : do another test with accolinearity_flag set to True

    # actors
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")

    # store phsp
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attributes = [
        "EventID",
        "TrackID",
        "EventPosition",
        "EventDirection",
        "KineticEnergy",
        "ParticleName",
        "TimeFromBeginOfEvent",
        "GlobalTime",
        "LocalTime",
        "PDGCode",
        "PostPosition",
        "PostDirection",
    ]
    phsp.output = paths.output / "b2b.root"

    # verbose
    # sim.g4_verbose = True
    # sim.add_g4_command_after_init("/tracking/verbose 2")
    # sim.add_g4_command_after_init("/run/verbose 2")
    # sim.add_g4_command_after_init("/event/verbose 2")
    # sim.add_g4_command_after_init("/tracking/verbose 1")

    # start simulation
    sim.run()

    # get results
    stats = sim.output.get_actor("Stats")
    print(stats)

    # FIXME : test something
    is_ok = False
    utility.test_ok(is_ok)

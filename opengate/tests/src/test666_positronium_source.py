#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test010_positronium_source", output_folder="test666"
    )
    print("starting")

    # create the simulation
    sim = gate.Simulation()
    sim.physics_manager.physics_list_name = 'G4EmLivermorePolarizedPhysics'
    sim.physics_manager.enable_decay = True

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
    source = sim.add_source("PositroniumSource", "source1")
    source.particle = "gamma"
    source.activity = 1000 * Bq / sim.number_of_threads
    source.position.type = "sphere"
    source.position.radius = 5 * mm
    source.position.translation = [-3 * cm, 30 * cm, -3 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, -1, 0]
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV

    # print(sim.physics_manager.dump_available_physics_lists())

    # source = sim.add_source("PositroniumSource", "s3")
    # source.particle = "proton"
    # source.activity = 10000 * Bq / sim.number_of_threads
    # source.position.type = "box"
    # source.position.size = [4 * cm, 4 * cm, 4 * cm]
    # source.position.translation = [8 * cm, 8 * cm, 30 * cm]
    # source.direction.type = "focused"
    # source.direction.focus_point = [1 * cm, 2 * cm, 3 * cm]
    # source.energy.type = "gauss"
    # source.energy.mono = 140 * MeV
    # source.energy.sigma_gauss = 10 * MeV

    # source = sim.add_source("PositroniumSource", "s4")
    # source.particle = "proton"
    # source.activity = 10000 * Bq / sim.number_of_threads
    # source.position.type = "box"
    # source.position.size = [4 * cm, 4 * cm, 4 * cm]
    # source.position.translation = [-3 * cm, -3 * cm, -3 * cm]
    # # source.position.rotation = Rotation.from_euler('x', 45, degrees=True).as_matrix()
    # source.position.rotation = Rotation.identity().as_matrix()
    # source.direction.type = "iso"
    # source.energy.type = "gauss"
    # source.energy.mono = 80 * MeV
    # source.energy.sigma_gauss = 1 * MeV

    # actors
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats_actor.track_types_flag = True

    # PhaseSpace Actor
    ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    ta2.attached_to = waterbox.name
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
    ta2.debug =True 
    ta2.output_filename = "testblabla.root"

    # run the simulation once with no particle in the phsp
    source.direction.momentum = [0, 0, 1]



    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")
    # sim.g4_commands_after_init.append("/run/verbose 2")
    # sim.g4_commands_after_init.append("/event/verbose 2")
    # sim.g4_commands_after_init.append("/tracking/verbose 1")

    # start simulation
    print("just before running the simulation")
    sim.run()

    # # print
    print("Simulation seed:", sim.current_random_seed)

    # # get results
    print(stats_actor)

    # utility.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility


# Units
MeV = gate.g4_units.MeV
keV = gate.g4_units.keV
Bq = gate.g4_units.Bq
deg = gate.g4_units.deg
mm = gate.g4_units.mm
m = gate.g4_units.m
cm = gate.g4_units.cm

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test010_positronium_source", output_folder="test666"
    )
    print("Starting")

    # create the simulation
    sim = gate.Simulation()
    sim.physics_manager.physics_list_name = 'G4EmLivermorePolarizedPhysics'
    # sim.physics_manager.enable_decay = True

    # main options
    # sim.g4_verbose = True 
    sim.g4_verbose = False 
    sim.g4_verbose_level = 1
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.number_of_threads = 1
    sim.random_seed = 123456
    sim.output_dir = paths.output

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
    source.position.radius = 2 * mm
    # source.position.translation = [-3 * cm, -3 * cm, -3 * cm]

    # print(sim.physics_manager.dump_available_physics_lists())


    # actors
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats_actor.track_types_flag = True

    # PhaseSpace Actor
    ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    # ta2.attached_to = waterbox.name
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
    ta2.steps_to_store = "first"
    ta2.output_filename = "output_positrionium.root"



    # sim.g4_commands_after_init.append("/tracking/verbose 0")
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

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
ns = gate.g4_units.ns

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__,
                                           "gate_test666_positronium_source",
                                           output_folder="test666")
    print("Starting")

    # create the simulation
    sim = gate.Simulation()
    sim.physics_manager.physics_list_name = 'G4EmLivermorePolarizedPhysics'

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = True
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
    source = sim.add_source("PositroniumSource", "source")
    source.activity = 1000 * Bq / sim.number_of_threads
    #source.position.type = "sphere"
    #source.position.radius = 2 * mm

    source.positronium_fractions = [0.4, 0.3, 0.2, 0.1]
    source.positronium_lifetimes = [0.122 * ns, 2 * ns, 5 * ns, 12 * ns]
    source.decay_kinds = ["k2Gamma", "k2Gamma", "k3Gamma", "k2Gamma"]
    source.prompt_photon_probabilities = [0.1, 1., 1., 0.5]
    source.prompt_photon_energies = [1.244 * MeV, 1 * MeV, 1.2 * MeV, 2 * MeV]

    # actors
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats_actor.track_types_flag = True

    # PhaseSpace Actor
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attributes = [
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
    phsp.debug = True
    phsp.steps_to_store = "first"
    phsp.output_filename = "output_positronium.root"

    # start simulation
    sim.run()

    # get results
    print(stats_actor)

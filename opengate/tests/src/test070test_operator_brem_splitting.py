#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
import numpy as np
from scipy.spatial.transform import Rotation
from opengate.tests import utility


def validation_test(arr, nb_split, tol=0.02):
    arr = arr[arr["ParticleName"] == "gamma"]
    EventID = arr["EventID"]
    Weights = arr["Weight"][EventID == EventID[0]]
    sum_Weights = np.round(np.sum(Weights), 4)
    if (
        sum_Weights > 1 - tol
        and sum_Weights < 1 + tol
        and len(Weights) > nb_split * (1 - tol)
        and len(Weights) < nb_split * (1 + tol)
    ):
        return True
    else:
        return False


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "test070test_operator_brem_splitting", output_folder="test070"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    # ui.visu = True
    # ui.visu_type = "vrml"
    ui.check_volumes_overlap = False
    # ui.running_verbose_level = gate.EVENT
    ui.number_of_threads = 1
    ui.random_seed = "auto"

    # units
    m = gate.g4_units.m
    km = gate.g4_units.km
    mm = gate.g4_units.mm
    um = gate.g4_units.um
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    gcm3 = gate.g4_units.g / gate.g4_units.cm3

    #  adapt world size
    world = sim.world
    world.size = [1 * m, 1 * m, 2 * m]
    world.material = "G4_Galactic"

    ####### GEOMETRY TO IRRADIATE #############
    sim.volume_manager.material_database.add_material_weights(
        "Tungsten",
        ["W"],
        [1],
        19.3 * gcm3,
    )

    W_tubs = sim.add_volume("Tubs", "W_box")
    W_tubs.material = "Tungsten"
    W_tubs.mother = world.name

    W_tubs.rmin = 0
    W_tubs.rmax = 0.1 * um
    W_tubs.dz = 0.5 * m
    W_tubs.color = [0.8, 0.2, 0.1, 1]
    angle_x = np.random.randint(0, 360)
    angle_y = np.random.randint(0, 360)
    angle_z = np.random.randint(0, 360)
    # angle_x = 45
    # angle_y = 70
    # angle_z = 80

    rotation = Rotation.from_euler(
        "xyz", [angle_y, angle_y, angle_z], degrees=True
    ).as_matrix()
    W_tubs.rotation = rotation

    ######## BremSplitting ACTOR #########
    nb_split = 100
    brem_splitting_actor = sim.add_actor("BremSplittingActor", "eBremSplittingW")
    brem_splitting_actor.mother = W_tubs.name
    brem_splitting_actor.splitting_factor = nb_split
    # brem_splitting_actor.processes is not used in the cpp part, it's juste here for a more confortable user utilization
    list_processes_to_bias = brem_splitting_actor.processes

    ##### PHASE SPACE plan ######"
    plan_tubs = sim.add_volume("Tubs", "phsp_tubs")
    plan_tubs.material = "G4_Galactic"
    plan_tubs.mother = world.name
    plan_tubs.rmin = 0.11 * um
    plan_tubs.rmax = 0.11 * um + 1 * nm
    plan_tubs.dz = 0.5 * m
    plan_tubs.color = [0.2, 1, 0.8, 1]
    plan_tubs.rotation = rotation

    ####### Electron source ###########
    source = sim.add_source("GenericSource", "source1")
    source.particle = "e-"
    source.n = 10000
    source.position.type = "sphere"
    source.position.radius = 1 * nm
    source.direction.type = "momentum"
    source.direction.momentum = np.dot(rotation, np.array([0, 0, 1]))
    source.energy.type = "mono"
    source.energy.mono = 6 * MeV

    ####### PHASE SPACE ACTOR ##############

    phsp_actor = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp_actor.mother = plan_tubs.name
    phsp_actor.attributes = [
        "EventID",
        "Weight",
        "ParticleName",
    ]

    phsp_actor.output = paths.output / "test070_output_data.root"

    ##### MODIFIED PHYSICS LIST ###############

    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    ### Perhaps avoid the user to call the below boolean function ? ###
    sim.physics_manager.special_physics_constructors.G4GenericBiasingPhysics = True
    sim.physics_manager.processes_to_bias.electron = list_processes_to_bias
    sim.physics_manager.processes_to_bias.positron = list_processes_to_bias

    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * um
    sim.physics_manager.global_production_cuts.positron = 1 * km

    output = sim.run()

    #
    # # print results
    stats = sim.output.get_actor("Stats")
    h = sim.output.get_actor("PhaseSpace")
    print(stats)
    #
    f_phsp = uproot.open(paths.output / "test070_output_data.root")
    arr = f_phsp["PhaseSpace"].arrays()

    is_ok = validation_test(arr, nb_split)
    utility.test_ok(is_ok)

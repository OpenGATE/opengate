#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import scipy
from scipy.spatial.transform import Rotation
from opengate.tests import utility


def validation_test(arr, NIST_data, nb_split, tol=0.01):
    tab_ekin = NIST_data[:, 0]
    mu_att = NIST_data[:, -2]

    log_ekin = np.log(tab_ekin)
    log_mu = np.log(mu_att)

    f_mu = scipy.interpolate.interp1d(log_ekin, log_mu, kind="cubic")
    # print(arr["TrackCreatorProcess"])
    Tracks = arr[
        (arr["TrackCreatorProcess"] == "biasWrapper(compt)")
        & (arr["KineticEnergy"] > 0.1)
        & (arr["ParticleName"] == "gamma")
        & (arr["Weight"] > 10 ** (-20))
    ]
    ekin_tracks = Tracks["KineticEnergy"]
    x_vertex = Tracks["TrackVertexPosition_X"]
    y_vertex = Tracks["TrackVertexPosition_Y"]
    z_vertex = Tracks["TrackVertexPosition_Z"]
    x = Tracks["PrePosition_X"]
    y = Tracks["PrePosition_Y"]
    z = Tracks["PrePosition_Z"]
    weights = Tracks["Weight"] * nb_split
    dist = np.sqrt((x - x_vertex) ** 2 + (y - y_vertex) ** 2 + (z - z_vertex) ** 2)

    G4_mu = -np.log(weights) / (0.1 * dist * 19.3)
    X_com_mu = np.exp(f_mu(np.log(ekin_tracks)))
    diff = (G4_mu - X_com_mu) / G4_mu
    print(
        "Median difference between mu calculated from XCOM database and from GEANT4 free flight operation:",
        np.round(100 * np.median(diff), 1),
        "%",
    )
    return np.median(diff) < tol


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "test072_pseudo_transportation", output_folder="test072"
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
    deg = gate.g4_units.deg

    #  adapt world size
    world = sim.world
    world.size = [1.2 * m, 1.2 * m, 2 * m]
    world.material = "G4_Galactic"

    ####### GEOMETRY TO IRRADIATE #############
    sim.volume_manager.material_database.add_material_weights(
        "Tungsten",
        ["W"],
        [1],
        19.3 * gcm3,
    )
    simple_collimation = sim.add_volume("Box", "colli_box")
    simple_collimation.material = "G4_Galactic"
    simple_collimation.mother = world.name
    simple_collimation.size = [1 * m, 1 * m, 40 * cm]
    simple_collimation.color = [0.3, 0.1, 0.8, 1]

    W_leaf = sim.add_volume("Box", "W_leaf")
    W_leaf.mother = simple_collimation.name
    W_leaf.size = [1 * m, 1 * m, 2 * cm]
    W_leaf.material = "Tungsten"
    leaf_translation = []
    for i in range(10):
        leaf_translation.append(
            [
                0,
                0,
                -0.5 * simple_collimation.size[2]
                + 0.5 * W_leaf.size[2]
                + i * W_leaf.size[2],
            ]
        )
    print(leaf_translation)
    W_leaf.translation = leaf_translation
    W_leaf.color = [0.8, 0.2, 0.1, 1]

    ######## pseudo_transportation ACTOR #########
    nb_split = 5
    pseudo_transportation_actor = sim.add_actor(
        "ComptPseudoTransportationActor", "pseudo_transportation_actor"
    )
    pseudo_transportation_actor.mother = simple_collimation.name
    pseudo_transportation_actor.splitting_factor = nb_split
    pseudo_transportation_actor.relative_min_weight_of_particle = np.inf
    list_processes_to_bias = pseudo_transportation_actor.gamma_processes

    ##### PHASE SPACE plan ######"
    plan = sim.add_volume("Box", "phsp")
    plan.material = "G4_Galactic"
    plan.mother = world.name
    plan.size = [1 * m, 1 * m, 1 * nm]
    plan.color = [0.2, 1, 0.8, 1]
    plan.translation = [0, 0, -20 * cm - 1 * nm]

    ####### gamma source ###########
    source = sim.add_source("GenericSource", "source1")
    source.particle = "gamma"
    source.n = 1000
    source.position.type = "sphere"
    source.position.radius = 1 * nm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, -1]
    source.energy.type = "mono"
    source.energy.mono = 6 * MeV
    source.position.translation = [0, 0, 18 * cm]

    ####### PHASE SPACE ACTOR ##############

    phsp_actor = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp_actor.mother = plan.name
    phsp_actor.attributes = [
        "EventID",
        "TrackCreatorProcess",
        "TrackVertexPosition",
        "PrePosition",
        "Weight",
        "KineticEnergy",
        "ParentID",
        "ParticleName",
    ]

    phsp_actor.output = paths.output / "test072_output_data.root"

    ##### MODIFIED PHYSICS LIST ###############

    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    ### Perhaps avoid the user to call the below boolean function ? ###
    sim.physics_manager.special_physics_constructors.G4GenericBiasingPhysics = True
    sim.physics_manager.processes_to_bias.gamma = list_processes_to_bias
    s = f"/process/em/UseGeneralProcess false"
    sim.add_g4_command_before_init(s)

    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * km
    sim.physics_manager.global_production_cuts.positron = 1 * km

    output = sim.run()

    #
    # # print results
    stats = sim.output.get_actor("Stats")
    h = sim.output.get_actor("PhaseSpace")
    print(stats)
    #
    f_phsp = uproot.open(paths.output / "test072_output_data.root")
    data_NIST_W = np.loadtxt(paths.data / "NIST_W.txt", delimiter="|")
    arr = f_phsp["PhaseSpace"].arrays()
    #
    is_ok = validation_test(arr, data_NIST_W, nb_split)
    utility.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
import numpy as np
from scipy.spatial.transform import Rotation
from opengate.tests import utility


def validation_test_RR(
    arr_data, rotation, vector_of_direction, theta, nb_splitting, tol_weights=0.08
):
    arr_data = arr_data[
        (arr_data["TrackCreatorProcess"] != "phot")
        & (arr_data["TrackCreatorProcess"] != "eBrem")
        & (arr_data["TrackCreatorProcess"] != "eIoni")
        & (arr_data["ParticleName"] == "gamma")
    ]
    EventID = arr_data["EventID"]
    list_of_weights = []
    weights = 0
    for i in range(len(EventID)):
        if i == 0:
            weights += arr_data["Weight"][i]
        else:
            if EventID[i] == EventID[i - 1]:
                weights += arr_data["Weight"][i]
            else:
                list_of_weights.append(weights)
                weights = arr_data["Weight"][i]
    list_of_weights = np.array(list_of_weights)
    mean_weights = np.mean(list_of_weights)
    bool_weight = False
    if 1 - tol_weights < mean_weights < 1 + tol_weights:
        bool_weight = True
    weights = arr_data["Weight"][EventID == EventID[0]]
    rotated_vector = np.dot(rotation, np.array(vector_of_direction))
    # 2.418766
    arr_first_evt = arr_data[EventID == EventID[0]]
    arr_first_evt_dir_X = arr_first_evt["PreDirection_X"].to_numpy()
    arr_first_evt_dir_Y = arr_first_evt["PreDirection_Y"].to_numpy()
    arr_first_evt_dir_Z = arr_first_evt["PreDirection_Z"].to_numpy()

    arr_first_evt_dir = np.transpose(
        np.array([arr_first_evt_dir_X, arr_first_evt_dir_Y, arr_first_evt_dir_Z])
    )
    tab_costheta = np.sum(rotated_vector * arr_first_evt_dir, axis=1)
    tab_theta = np.arccos(tab_costheta) * 180 / np.pi * deg

    bool_russian_roulette_1 = bool(
        1 - np.sum((tab_theta[weights == 1 / nb_splitting] > theta))
    )
    bool_russian_roulette_2 = bool(1 - np.sum((tab_theta[weights == 1] <= theta)))
    print("Average weight of :", mean_weights)
    if bool_russian_roulette_1 and bool_russian_roulette_2 and bool_weight:
        return True
    else:
        return False


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "test071test_operator_compt_splitting_RR", output_folder="test071"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    # ui.visu = True
    # ui.visu_type = "vrml"
    ui.check_volumes_overlap = False
    # ui.running_verbose_level = gate.logger.EVENT
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
    world.size = [0.25 * m, 0.25 * m, 0.25 * m]
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
    W_tubs.rmax = 0.001 * um
    W_tubs.dz = 0.05 * m
    W_tubs.color = [0.8, 0.2, 0.1, 1]
    angle_x = 45
    angle_y = 70
    angle_z = 80
    # angle_x = 0
    # angle_y = 0
    # angle_z = 0

    rotation = Rotation.from_euler(
        "xyz", [angle_y, angle_y, angle_z], degrees=True
    ).as_matrix()
    W_tubs.rotation = rotation

    ####### Compton Splitting ACTOR #########
    nb_split = 19.4
    theta_max = 90 * deg
    compt_splitting_actor = sim.add_actor("ComptSplittingActor", "ComptSplittingW")
    compt_splitting_actor.mother = W_tubs.name
    compt_splitting_actor.splitting_factor = nb_split
    compt_splitting_actor.russian_roulette = True
    compt_splitting_actor.rotation_vector_director = True
    compt_splitting_actor.vector_director = [0, 0, -1]

    compt_splitting_actor.max_theta = theta_max
    list_processes_to_bias = compt_splitting_actor.processes

    ##### PHASE SPACE plan ######"
    plan_tubs = sim.add_volume("Tubs", "phsp_tubs")
    plan_tubs.material = "G4_Galactic"
    plan_tubs.mother = world.name
    plan_tubs.rmin = W_tubs.rmax
    plan_tubs.rmax = plan_tubs.rmin + 1 * nm
    plan_tubs.dz = 0.5 * m
    plan_tubs.color = [0.2, 1, 0.8, 1]
    plan_tubs.rotation = rotation

    ####### Gamma source ###########
    source = sim.add_source("GenericSource", "source1")
    source.particle = "gamma"
    source.n = 1000
    source.position.type = "sphere"
    source.position.radius = 1 * nm
    source.direction.type = "momentum"
    source.direction.momentum = np.dot(rotation, np.array([0, 0, -1]))
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV

    ####### PHASE SPACE ACTOR ##############

    phsp_actor = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp_actor.mother = plan_tubs.name
    phsp_actor.attributes = [
        "EventID",
        "TrackID",
        "Weight",
        "ParticleName",
        "KineticEnergy",
        "PreDirection",
        "TrackCreatorProcess",
    ]

    phsp_actor.output = paths.output / "test071_output_data_RR.root"

    ##### MODIFIED PHYSICS LIST ###############

    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option2"
    ## Perhaps avoid the user to call the below boolean function ? ###
    sim.physics_manager.special_physics_constructors.G4GenericBiasingPhysics = True
    sim.physics_manager.processes_to_bias.gamma = list_processes_to_bias
    #### Extremely important, it seems that GEANT4, for almost all physics lists, encompass all the photon processes in GammaGeneralProc
    #### Therefore if we provide the name of the real process (here compt) without deactivating GammaGeneralProcess, it will not find the
    #### process to bias and the biasing will fail
    s = f"/process/em/UseGeneralProcess false"
    sim.add_g4_command_before_init(s)

    sim.physics_manager.global_production_cuts.gamma = 1 * m
    sim.physics_manager.global_production_cuts.electron = 1 * um
    sim.physics_manager.global_production_cuts.positron = 1 * km

    output = sim.run()

    #
    # print results
    stats = sim.output.get_actor("Stats")
    h = sim.output.get_actor("PhaseSpace")

    f_data = uproot.open(paths.output / "test071_output_data_RR.root")
    arr_data = f_data["PhaseSpace"].arrays()

    is_ok = validation_test_RR(
        arr_data, rotation, compt_splitting_actor.vector_director, theta_max, nb_split
    )
    utility.test_ok(is_ok)

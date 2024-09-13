#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate_core as g4
import opengate as gate
import uproot
import numpy as np
from scipy.spatial.transform import Rotation
from opengate.tests import utility


def check_process_user_hook(simulaton_engine):
    # Check whether the particle 'gamma' actually has
    # the requested processes attached to it
    p_name = "gamma"
    g4_particle_table = g4.G4ParticleTable.GetParticleTable()
    particle = g4_particle_table.FindParticle(particle_name=p_name)
    # FindParticle returns nullptr if particle name was not found
    if particle is None:
        raise Exception(f"Something went wrong. Could not find particle {p_name}.")
    pm = particle.GetProcessManager()
    p = pm.GetProcess("compt")
    # GetProcess returns nullptr if the requested process was not found
    if p is None:
        raise Exception(f"Could not find the compt process for particle {p_name}.")
    else:
        print(f"Hooray, I found the process compt for the particle {p_name}!")


def bool_validation_test(dico_parameters, tol):
    keys = dico_parameters.keys()
    liste_diff_max = []
    for key in keys:
        liste_diff_max.append(np.max(dico_parameters[key]))
    liste_diff_max = np.asarray(liste_diff_max)
    max_diff = np.max(liste_diff_max)
    print(
        "Maximal error (mean or std dev) measured between the analog and the biased simulation:",
        np.round(max_diff, 2),
        "%",
    )
    if max_diff <= 100 * tol:
        return True
    else:
        return False


def validation_test(arr_ref, arr_data, nb_split, tol=0.2, tol_weights=0.04):
    arr_ref = arr_ref[
        (arr_ref["TrackCreatorProcess"] == "compt")
        | (arr_ref["TrackCreatorProcess"] == "none")
    ]
    arr_data = arr_data[
        (arr_data["TrackCreatorProcess"] != "phot")
        & (arr_data["TrackCreatorProcess"] != "eBrem")
        & (arr_data["TrackCreatorProcess"] != "eIoni")
    ]

    EventID = arr_data["EventID"]
    weights = arr_data["Weight"][EventID == EventID[0]]
    val_weights = np.round(weights[0], 4)
    bool_val_weights = 1 / nb_split == val_weights
    print(
        "Sum of electron and photon weights for the first event simulated:",
        np.round(np.sum(weights), 2),
    )
    print("Len of the weights vector for the first event:", len(weights))
    condition_weights = np.round(np.sum(weights), 4) > 2 * (
        1 - tol_weights
    ) and np.round(np.sum(weights), 4) < 2 * (1 + tol_weights)
    condition_len = len(weights) > 2 * nb_split * (1 - tol_weights) and len(
        weights
    ) < 2 * nb_split * (1 + tol_weights)
    bool_weights = condition_weights and condition_len
    keys = ["KineticEnergy", "PreDirection_X", "PreDirection_Y", "PreDirection_Z"]

    arr_ref_phot = arr_ref[arr_ref["ParticleName"] == "gamma"]
    arr_ref_elec = arr_ref[arr_ref["ParticleName"] == "e-"]

    arr_data_phot = arr_data[arr_data["ParticleName"] == "gamma"]
    arr_data_elec = arr_data[arr_data["ParticleName"] == "e-"]

    keys_dico = ["ref", "data"]
    dico_arr_phot = {}
    dico_arr_elec = {}

    dico_arr_phot["ref"] = arr_ref_phot
    dico_arr_phot["data"] = arr_data_phot

    dico_arr_elec["ref"] = arr_ref_elec
    dico_arr_elec["data"] = arr_data_elec
    dico_comp_data = {}

    for key in keys:
        arr_data = []
        for key_dico in keys_dico:
            mean_elec = np.mean(dico_arr_phot[key_dico][key])
            mean_phot = np.mean(dico_arr_elec[key_dico][key])
            std_elec = np.std(dico_arr_phot[key_dico][key])
            std_phot = np.std(dico_arr_elec[key_dico][key])
            arr_data += [mean_elec, mean_phot, std_elec, std_phot]
        dico_comp_data[key] = 100 * np.abs(
            np.array(
                [
                    (arr_data[0] - arr_data[4]) / arr_data[0],
                    (arr_data[1] - arr_data[5]) / arr_data[1],
                    (arr_data[2] - arr_data[6]) / arr_data[6],
                    (arr_data[3] - arr_data[7]) / arr_data[3],
                ]
            )
        )
    bool_test = bool_validation_test(dico_comp_data, tol)
    bool_tot = bool_test and bool_weights and bool_val_weights
    return bool_tot


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "test071test_operator_compt_splitting", output_folder="test071"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    # sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    # sim.running_verbose_level = gate.logger.EVENT
    sim.number_of_threads = 1
    sim.random_seed = "auto"
    sim.output_dir = paths.output

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

    W_tubs.rmin = 0
    W_tubs.rmax = 0.001 * um
    W_tubs.dz = 0.05 * m
    W_tubs.color = [0.8, 0.2, 0.1, 1]
    angle_x = 45
    angle_y = 70
    angle_z = 80

    rotation = Rotation.from_euler(
        "xyz", [angle_y, angle_y, angle_z], degrees=True
    ).as_matrix()
    W_tubs.rotation = rotation

    ####### Compton Splitting ACTOR #########
    nb_split = 100
    compt_splitting_actor = sim.add_actor("ComptSplittingActor", "ComptSplittingW")
    compt_splitting_actor.attached_to = W_tubs.name
    compt_splitting_actor.splitting_factor = nb_split
    # compt_splitting_actor.particles = 'gamma'

    ##### PHASE SPACE plan ######"
    plan_tubs = sim.add_volume("Tubs", "phsp_tubs")
    plan_tubs.material = "G4_Galactic"
    plan_tubs.mother = world.name
    plan_tubs.rmin = W_tubs.rmax
    plan_tubs.rmax = plan_tubs.rmin + 1 * nm
    plan_tubs.dz = 0.5 * m
    plan_tubs.color = [0.2, 1, 0.8, 1]
    plan_tubs.rotation = rotation

    ####### Electron source ###########
    source = sim.add_source("GenericSource", "source1")
    source.particle = "gamma"
    source.n = 5000
    source.position.type = "sphere"
    source.position.radius = 1 * nm
    source.direction.type = "momentum"
    # source.direction.momentum = [0,0,-1]
    source.direction.momentum = np.dot(rotation, np.array([0, 0, -1]))
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV

    ####### PHASE SPACE ACTOR ##############

    phsp_actor = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp_actor.attached_to = plan_tubs.name
    phsp_actor.attributes = [
        "EventID",
        "TrackID",
        "Weight",
        "ParticleName",
        "KineticEnergy",
        "PreDirection",
        "TrackCreatorProcess",
    ]

    phsp_actor.output_filename = "test071_output_data.root"

    ##### MODIFIED PHYSICS LIST ###############

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option2"
    #### Extremely important, it seems that GEANT4, for almost all physics lists, encompass all the photon processes in GammaGeneralProc
    #### Therefore if we provide the name of the real process (here compt) without deactivating GammaGeneralProcess, it will not find the
    #### process to bias and the biasing will fail
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)

    sim.physics_manager.global_production_cuts.gamma = 1 * m
    sim.physics_manager.global_production_cuts.electron = 1 * um
    sim.physics_manager.global_production_cuts.positron = 1 * km

    sim.user_hook_after_run = check_process_user_hook

    sim.run()

    #
    # print results
    print(stats)
    #
    f_data = uproot.open(phsp_actor.get_output_path())
    f_ref_data = uproot.open(paths.data / "test071_ref_data.root")
    arr_data = f_data["PhaseSpace"].arrays()
    arr_ref_data = f_ref_data["PhaseSpace"].arrays()
    #
    is_ok = validation_test(arr_ref_data, arr_data, nb_split)
    utility.test_ok(is_ok)

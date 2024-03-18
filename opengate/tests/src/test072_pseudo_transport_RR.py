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


def Ekin_per_event(weight, EventID, Ekin):
    l_edep = []
    Edep_per_event = 0
    last_EventID = 0
    for i in range(len(weight)):
        if i > 0:
            last_EventID = EventID[i - 1]
        if EventID[i] != last_EventID and i > 0:
            l_edep.append(Edep_per_event)
            Edep_per_event = 0
        Edep_per_event += Ekin[i] * weight[i]
    return np.asarray(l_edep)


def validation_test(arr_no_RR, arr_RR, nb_event, splitting_factor, tol=0.15):

    Tracks_no_RR = arr_no_RR[
        (arr_no_RR["TrackCreatorProcess"] == "biasWrapper(compt)")
        & (arr_no_RR["ParticleName"] == "gamma")
    ]

    Tracks_RR = arr_RR[
        (arr_RR["TrackCreatorProcess"] == "biasWrapper(compt)")
        & (arr_RR["ParticleName"] == "gamma")
    ]

    Ekin_no_RR = Tracks_no_RR["KineticEnergy"]
    w_no_RR = Tracks_no_RR["Weight"]
    Event_ID_no_RR = Tracks_no_RR["EventID"]

    Ekin_per_event_no_RR = Ekin_per_event(w_no_RR, Event_ID_no_RR, Ekin_no_RR)

    Ekin_RR = Tracks_RR["KineticEnergy"]
    w_RR = Tracks_RR["Weight"]
    Event_ID_RR = Tracks_RR["EventID"]

    bool_RR = (np.min(w_RR) > 0.1 * 1 / splitting_factor) & (
        np.max(w_RR) < 1 / splitting_factor
    )

    Ekin_per_event_RR = Ekin_per_event(w_RR, Event_ID_RR, Ekin_RR)

    mean_ekin_event_no_RR = np.sum(Ekin_per_event_no_RR) / nb_event
    mean_ekin_event_RR = np.sum(Ekin_per_event_RR) / nb_event
    diff = (mean_ekin_event_RR - mean_ekin_event_no_RR) / mean_ekin_event_RR
    print(
        "Mean kinetic energy per event without russian roulette :",
        np.round(1000 * mean_ekin_event_no_RR, 1),
        "keV",
    )
    print(
        "Mean kinetic energy per event with russian roulette :",
        np.round(1000 * mean_ekin_event_RR, 1),
        "keV",
    )
    print("Percentage of difference :", diff * 100, "%")

    return (abs(diff) < tol) & (bool_RR)
    # mean_energy_per_history_no_RR = np.sum(Tracks_no_RR["KineticEnergy"]*Tracks_no_RR["Weight"])/nb_event
    # mean_energy_per_history_RR = np.sum(Tracks_RR["KineticEnergy"] * Tracks_RR["Weight"]) / nb_event

    # print(mean_energy_per_history_no_RR,mean_energy_per_history_RR)


if __name__ == "__main__":

    for j in range(2):
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
        W_leaf.size = [1 * m, 1 * m, 0.5 * cm]
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
        W_leaf.translation = leaf_translation
        W_leaf.color = [0.8, 0.2, 0.1, 1]

        ######## pseudo_transportation ACTOR #########
        nb_split = 5
        pseudo_transportation_actor = sim.add_actor(
            "ComptPseudoTransportationActor", "pseudo_transportation_actor"
        )
        pseudo_transportation_actor.mother = simple_collimation.name
        pseudo_transportation_actor.splitting_factor = nb_split
        pseudo_transportation_actor.relative_min_weight_of_particle = 10000
        if j == 0:
            pseudo_transportation_actor.russian_roulette_for_weights = False
        if j == 1:
            pseudo_transportation_actor.russian_roulette_for_weights = True
        list_processes_to_bias = pseudo_transportation_actor.gamma_processes

        ##### PHASE SPACE plan ######"
        plan = sim.add_volume("Box", "phsp")
        plan.material = "G4_Galactic"
        plan.mother = world.name
        plan.size = [1 * m, 1 * m, 1 * nm]
        plan.color = [0.2, 1, 0.8, 1]
        plan.translation = [0, 0, -20 * cm - 1 * nm]

        ####### gamma source ###########
        nb_event = 20000
        source = sim.add_source("GenericSource", "source1")
        source.particle = "gamma"
        source.n = nb_event
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
        data_name = "test072_output_data_RR_" + str(j) + ".root"
        phsp_actor.output = paths.output / data_name

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

        output = sim.run(True)

        #
        # # print results
        stats = sim.output.get_actor("Stats")
        h = sim.output.get_actor("PhaseSpace")
        print(stats)
        #

    f_1 = uproot.open(paths.output / "test072_output_data_RR_0.root")
    f_2 = uproot.open(paths.output / "test072_output_data_RR_1.root")

    arr_no_RR = f_1["PhaseSpace"].arrays()
    arr_RR = f_2["PhaseSpace"].arrays()

    is_ok = validation_test(arr_no_RR, arr_RR, nb_event, nb_split)
    utility.test_ok(is_ok)

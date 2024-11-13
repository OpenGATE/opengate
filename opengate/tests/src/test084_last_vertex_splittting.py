#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
import numpy as np
from scipy.spatial.transform import Rotation
from opengate.tests import utility


def validation_test(arr_ref, arr_data, nb_split):
    arr_ref = arr_ref[arr_ref["ParticleName"] == "gamma"]
    arr_data = arr_data[arr_data["ParticleName"] == "gamma"]

    weight_data = np.round(np.mean(arr_data["Weight"]), 4)
    bool_weight = False
    print(
        "Weight mean is equal to", weight_data, "and need to be equal to", 1 / nb_split
    )
    if weight_data == 1 / nb_split:
        bool_weight = True

    bool_events = False
    sigma = np.sqrt((len(arr_data["KineticEnergy"]) / nb_split)) * nb_split
    nb_events_ref = len(arr_ref["KineticEnergy"])
    nb_events_data = len(arr_data["KineticEnergy"])
    print("Reference counts number:", nb_events_ref)
    print("Biased counts number:", nb_events_data)
    if nb_events_data - 4 * sigma <= nb_events_ref <= nb_events_data + 4 * sigma:
        bool_events = True

    keys = [
        "KineticEnergy",
        "PreDirection_X",
        "PreDirection_Y",
        "PreDirection_Z",
        "PrePosition_X",
        "PrePosition_Y",
    ]

    bool_distrib = True
    for key in keys:
        ref = arr_ref[key]
        data = arr_data[key]

        mean_ref = np.mean(ref)
        mean_data = np.mean(data)

        std_dev_ref = np.std(ref, ddof=1)
        std_dev_data = np.std(data, ddof=1)

        std_err_ref = std_dev_ref / np.sqrt(len(ref))
        std_err_data = std_dev_data / (nb_split * np.sqrt(len(data) / nb_split))

        print(
            key,
            "mean ref value:",
            np.round(mean_ref, 3),
            "+-",
            np.round(std_err_ref, 3),
        )
        print(
            key,
            "mean data value:",
            np.round(mean_data, 3),
            "+-",
            np.round(std_err_data, 3),
        )

        if (
            mean_data - 4 * np.sqrt(std_err_data**2 + std_err_ref**2) > mean_ref
        ) or (mean_data + 4 * np.sqrt(std_err_data**2 + std_err_ref**2) < mean_ref):
            bool_distrib = False

    if bool_distrib and bool_events and bool_weight:
        return True
    else:
        return False


if __name__ == "__main__":
    for i in range(2):
        if i == 0:
            bias = False
        else:
            bias = True
        paths = utility.get_default_test_paths(
            __file__, "test084_last_vertex_splitting", output_folder="test084"
        )

        # create the simulation
        sim = gate.Simulation()

        # main options
        ui = sim.user_info
        ui.g4_verbose = False
        ui.visu = False
        ui.visu_type = "vrml"
        ui.check_volumes_overlap = False
        ui.number_of_threads = 1
        ui.random_seed = 123456789

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
        deg = gate.g4_units.deg
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
        W_tubs.mother = world.name

        W_tubs.rmin = 0
        W_tubs.rmax = 0.4 * cm
        W_tubs.dz = 0.05 * m
        W_tubs.color = [0.8, 0.2, 0.1, 1]
        angle_x = 45
        angle_y = 70
        angle_z = 80

        rotation = Rotation.from_euler(
            "xyz", [angle_y, angle_y, angle_z], degrees=True
        ).as_matrix()
        W_tubs.rotation = rotation

        if bias:
            ###### Last vertex Splitting ACTOR #########
            nb_split = 10
            vertex_splitting_actor = sim.add_actor(
                "LastVertexInteractionSplittingActor", "vertexSplittingW"
            )
            vertex_splitting_actor.attached_to = W_tubs.name
            vertex_splitting_actor.splitting_factor = nb_split
            vertex_splitting_actor.angular_kill = True
            vertex_splitting_actor.vector_director = [0, 0, -1]
            vertex_splitting_actor.max_theta = 90 * deg
            vertex_splitting_actor.batch_size = 10

        plan = sim.add_volume("Box", "plan_phsp")
        plan.material = "G4_Galactic"
        plan.size = [5 * cm, 5 * cm, 1 * nm]
        plan.translation = [0, 0, -1 * cm]

        ####### gamma source ###########
        source = sim.add_source("GenericSource", "source1")
        source.particle = "gamma"
        source.n = 100000
        if bias:
            source.n = source.n / nb_split

        source.position.type = "sphere"
        source.position.radius = 1 * nm
        source.direction.type = "momentum"
        # source.direction.momentum = [0,0,-1]
        source.direction.momentum = np.dot(rotation, np.array([0, 0, -1]))
        source.energy.type = "mono"
        source.energy.mono = 4 * MeV
        #
        ###### LastVertexSource #############
        if bias:
            source_0 = sim.add_source("LastVertexSource", "source_vertex")
            source_0.n = 1

        ####### PHASE SPACE ACTOR ##############
        sim.output_dir = paths.output
        phsp_actor = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
        phsp_actor.attached_to = plan.name
        phsp_actor.attributes = [
            "EventID",
            "TrackID",
            "Weight",
            "ParticleName",
            "KineticEnergy",
            "PreDirection",
            "PrePosition",
            "TrackCreatorProcess",
        ]
        if bias:
            phsp_actor.output_filename = "test084_output_data_last_vertex_biased.root"
        else:
            phsp_actor.output_filename = "test084_output_data_last_vertex_ref.root"

        s = sim.add_actor("SimulationStatisticsActor", "Stats")
        s.track_types_flag = True
        sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
        s = f"/process/em/UseGeneralProcess false"
        sim.g4_commands_before_init.append(s)

        sim.physics_manager.global_production_cuts.gamma = 1 * mm
        sim.physics_manager.global_production_cuts.electron = 1000 * km
        sim.physics_manager.global_production_cuts.positron = 1000 * km

        output = sim.run(True)
        print(s)

    f_data = uproot.open(paths.output / "test084_output_data_last_vertex_biased.root")
    f_ref_data = uproot.open(paths.output / "test084_output_data_last_vertex_ref.root")
    arr_data = f_data["PhaseSpace"].arrays()
    arr_ref_data = f_ref_data["PhaseSpace"].arrays()
    # #
    is_ok = validation_test(arr_ref_data, arr_data, nb_split)
    utility.test_ok(is_ok)

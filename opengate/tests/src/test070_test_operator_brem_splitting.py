#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4
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
    process = "eBrem"
    p = pm.GetProcess(process)
    # GetProcess returns nullptr if the requested process was not found
    if p is None:
        raise Exception(
            f"Could not find the process '{process}' for particle {p_name}."
        )
    else:
        print(f"Hooray, I found the process '{process}' for the particle {p_name}!")


def validation_test(arr, nb_split, tol=0.02):
    arr = arr[arr["ParticleName"] == "gamma"]
    EventID = arr["EventID"]
    Weights = arr["Weight"][EventID == EventID[0]]
    sum_Weights = np.round(np.sum(Weights), 4)
    if 1 - tol < sum_Weights < 1 + tol and nb_split * (1 - tol) < len(
        Weights
    ) < nb_split * (1 + tol):
        return True
    else:
        print("Test failed:")
        print(f"{sum_Weights=} vs 1, tol={tol}")
        print(f"{Weights=}  {len(Weights)=}")
        print(f"{nb_split=}")
        return False


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "test070test_operator_brem_splitting", output_folder="test070"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    # sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    # sim.running_verbose_level = gate.EVENT
    sim.number_of_threads = 1
    sim.random_seed = 123456789
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
    sim.world.size = [1 * m, 1 * m, 2 * m]
    sim.world.material = "G4_Galactic"

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
    brem_splitting_actor.attached_to = W_tubs.name
    brem_splitting_actor.splitting_factor = nb_split
    brem_splitting_actor.particles = "e-", "e+"

    ##### PHASE SPACE plan ######"
    plan_tubs = sim.add_volume("Tubs", "phsp_tubs")
    plan_tubs.material = "G4_Galactic"
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
    phsp_actor.attached_to = plan_tubs
    phsp_actor.attributes = [
        "EventID",
        "Weight",
        "ParticleName",
    ]

    phsp_actor.output_filename = "test070_output_data.root"

    ##### MODIFIED PHYSICS LIST ###############

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * um
    sim.physics_manager.global_production_cuts.positron = 1 * km

    sim.user_hook_after_init = check_process_user_hook

    sim.run()

    #
    # # print results
    print(stats)
    #
    f_phsp = uproot.open(phsp_actor.get_output_path())
    arr = f_phsp["PhaseSpace"].arrays()

    is_ok = validation_test(arr, nb_split)
    utility.test_ok(is_ok)

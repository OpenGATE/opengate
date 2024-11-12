#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import numpy as np
from anytree import Node, RenderTree
import uproot


"""
The kill actor according processes is able to kill if a process occurred or if a process did not occured.
To verify it here, I shot 6 MeV gamma with high cut on electrons in a tungsten target. It means that I have 4 types 
of photons : without any interaction, just compton photons, conv and therefore compton, and brem (with or without cmpton)

With a interdiction for photons to exit the volume if they did not undergo a conv, combined with a kill if eBrem occured.
I normally just have photons created by annihilation which undergo or not a compton. The test is now straightforward: 
if the number of detected photons is equal to the number of detected photons and created by conv, and if in average, the 
energy at the vertex is different of the measured energy, the actor is working.

"""
def test083_test(df):

    photon_array  = df[df["PDGCode"] ==22]
    if len(photon_array) == len(photon_array[photon_array["TrackCreatorProcess"] == "annihil"]):
        if np.mean(photon_array["KineticEnergy"]) != np.mean(photon_array["TrackVertexKineticEnergy"]):
            return True
    return False



if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__)
    output_path = paths.output

    print(output_path)
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    # ui.visu = True
    ui.visu_type = "vrml"
    ui.check_volumes_overlap = False
    # ui.running_verbose_level = gate.logger.EVENT
    ui.number_of_threads = 1
    ui.random_seed = "auto"

    # units
    m = gate.g4_units.m
    km = gate.g4_units.km
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    sec = gate.g4_units.s
    gcm3 = gate.g4_units["g/cm3"]

    sim.volume_manager.material_database.add_material_weights(
        "Tungsten",
        ["W"],
        [1],
        19.3 * gcm3,
    )

    #  adapt world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_Galactic"

    source = sim.add_source("GenericSource", "photon_source")
    source.particle = "gamma"
    source.position.type = "box"
    source.mother = world.name
    source.position.size = [1*nm,1*nm,1*nm]
    source.position.translation = [0, 0, 10*cm + 1 * mm]
    source.direction.type = "momentum"
    source.direction_relative_to_attached_volume = True
    # source1.direction.focus_point = [0*cm, 0*cm, -5 *cm]
    source.direction.momentum = [0, 0, -1]
    source.energy.type = "mono"
    source.energy.mono = 6 * MeV
    source.n = 100000

    tungsten = sim.add_volume("Box", "tungsten_box")
    tungsten.size = [4 * cm, 4 * cm, 20  * cm]
    tungsten.material = "Tungsten"
    tungsten.mother = world.name
    tungsten.color = [0.5, 0.9, 0.3, 1]

    kill_proc_act = sim.add_actor("KillAccordingProcessesActor", "kill_proc_act")
    kill_proc_act.attached_to = tungsten.name
    kill_proc_act.processes_to_kill_if_occurence=["eBrem"]
    kill_proc_act.processes_to_kill_if_no_occurence = ["conv"]

    kill_plan  = sim.add_volume("Box", "plan")
    kill_plan.size = [4 * cm, 4 * cm, 1*nm]
    kill_plan.translation = [0,0, - tungsten.size[2]/2  - kill_plan.size[2]]


    kill_actor = sim.add_actor("KillActor", "kill_actor_plan")
    kill_actor.attached_to = kill_plan.name

    phsp_sphere = sim.add_volume("Sphere", "phsp_sphere")
    phsp_sphere.mother =world.name
    phsp_sphere.rmin = 15 *cm
    phsp_sphere.rmax = 15 * cm +1*nm


    sim.output_dir = output_path
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = phsp_sphere.name
    phsp.attributes = ["EventID", "TrackID", "KineticEnergy","TrackVertexKineticEnergy","TrackCreatorProcess","PDGCode"]
    name_phsp = "test083_" + phsp.name + ".root"
    phsp.output_filename= name_phsp






    #
    # kill_int_act = sim.add_actor("KillInteractingParticleActor", "killact")
    # kill_int_act.attached_to = tungsten.name
    #
    # entry_phase_space = sim.add_volume("Box", "entry_phase_space")
    # entry_phase_space.mother = big_box
    # entry_phase_space.size = [0.8 * m, 0.8 * m, 1 * nm]
    # entry_phase_space.material = "G4_AIR"
    # entry_phase_space.translation = [0, 0, 0.21 * m]
    # entry_phase_space.color = [0.5, 0.9, 0.3, 1]
    #
    # exit_phase_space_1 = sim.add_volume("Box", "exit_phase_space_1")
    # exit_phase_space_1.mother = actor_box
    # exit_phase_space_1.size = [0.6 * m, 0.6 * m, 1 * nm]
    # exit_phase_space_1.material = "G4_AIR"
    # exit_phase_space_1.translation = [0, 0, -0.3 * m + 1 * nm]
    # exit_phase_space_1.color = [0.5, 0.9, 0.3, 1]
    #
    # exit_phase_space_2 = sim.add_volume("Box", "exit_phase_space_2")
    # exit_phase_space_2.mother = world.name
    # exit_phase_space_2.size = [0.6 * m, 0.6 * m, 1 * nm]
    # exit_phase_space_2.material = "G4_AIR"
    # exit_phase_space_2.translation = [0, 0, -0.4 * m - 1 * nm]
    # exit_phase_space_2.color = [0.5, 0.9, 0.3, 1]
    #
    # # print(sim.volume_manager.dump_volume_tree())
    # liste_phase_space_name = [
    #     entry_phase_space.name,
    #     exit_phase_space_1.name,
    #     exit_phase_space_2.name,
    # ]
    #
    # sim.output_dir = paths.output
    # for name in liste_phase_space_name:
    #
    #     phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace_" + name)
    #     phsp.attached_to = name
    #     phsp.attributes = ["EventID", "TrackID", "KineticEnergy"]
    #     name_phsp = "test083_" + name + ".root"
    #     phsp.output_filename= name_phsp
    #
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * km
    sim.physics_manager.global_production_cuts.positron = 1 * mm
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)
    #
    # s = sim.add_actor("SimulationStatisticsActor", "Stats")
    # s.track_types_flag = True
    #
    # # go !
    sim.run()
    #
    phsp = uproot.open(
        str(output_path)
        + "/test083_PhaseSpace.root"
        + ":PhaseSpace")
    # exit_phase_space_1 = uproot.open(
    #     str(output_path)
    #     + "/test083_"
    #     + liste_phase_space_name[1]
    #     + ".root"
    #     + ":PhaseSpace_"
    #     + liste_phase_space_name[1]
    # )
    # exit_phase_space_2 = uproot.open(
    #     str(output_path)
    #     + "/test083_"
    #     + liste_phase_space_name[2]
    #     + ".root"
    #     + ":PhaseSpace_"
    #     + liste_phase_space_name[2]
    # )
    #
    df = phsp.arrays()
    # df_exit_1 = exit_phase_space_1.arrays()
    # df_exit_2 = exit_phase_space_2.arrays()
    #
    is_ok = test083_test(df)
    #
    utility.test_ok(is_ok)

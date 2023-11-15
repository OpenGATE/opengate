#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot
import numpy as np




def validation_test(n,n_measured):
    n_part_minus = n - 3*np.sqrt(n)
    n_part_max = n + 3 * np.sqrt(n)
    if n_part_minus <=n_measured <= n_part_max:
        return True
    else:
        return False


if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__)
    output_path = "/home/mjacquet/Software/gatePython/opengate/opengate/tests/output/test019/"

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    # ui.visu = True
    ui.visu_type = "vrml"
    ui.check_volumes_overlap = False
    # ui.running_verbose_level = gate.EVENT
    ui.number_of_threads = 1
    ui.random_seed = "auto"

    # units
    m = gate.g4_units("m")
    km = gate.g4_units("km")
    mm = gate.g4_units("mm")
    cm = gate.g4_units("cm")
    nm = gate.g4_units("nm")
    Bq = gate.g4_units("Bq")
    MeV = gate.g4_units("MeV")
    keV = gate.g4_units("keV")
    gcm3 = gate.g4_units("g/cm3")

    #  adapt world size
    world = sim.world
    world.size = [1 * m, 1 * m, 2 * m]
    world.material = "G4_Galactic"

    # source_1
    nb_part = 1000
    plane_1 = sim.add_volume("Box", "plan_1")
    plane_1.material = "G4_Galactic"
    plane_1.mother = world.name
    plane_1.size = [1 * m, 1 * m, 1 * nm]
    plane_1.color = [0.8, 0.2, 0.1, 1]

    source_1 = sim.add_source("PhaseSpaceSource", "phsp_source_global_1")
    source_1.mother = plane_1.name
    source_1.phsp_file = paths.output / "test019/test019_hits_phsp_source_global.root"
    source_1.position_key = "PrePosition"
    source_1.direction_key = "PreDirection"
    source_1.weight_key = "Weight"
    source_1.global_flag = False
    source_1.particle = "gamma"
    source_1.batch_size = 100
    source_1.override_position = True
    source_1.position.translation = [0, 0, 300]
    source_1.activity = nb_part*Bq


    # add phase space plan 1

    phsp_plane_1 = sim.add_volume("Box", "phase_space_plane_1")
    phsp_plane_1.mother = world.name
    phsp_plane_1.material = "G4_Galactic"
    phsp_plane_1.size = [1 * m, 1 * m, 1 * nm]
    phsp_plane_1.translation = [0, 0, - 1000 *nm]
    phsp_plane_1.color = [1, 0, 0, 1]  # red

    phsp_actor = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp_actor.mother = phsp_plane_1.name
    phsp_actor.attributes = [
        "KineticEnergy",
    ]
    
    
    phsp_actor.output = paths.output / "test065_output_data.root"

    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    p = sim.get_physics_user_info()
    p.physics_list_name = "G4EmStandardPhysics_option3"
    p.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * mm
    sim.physics_manager.global_production_cuts.positron = 1 * mm
    #
    # # go !
    output = sim.start()


    #
    # # print results
    stats = sim.output.get_actor("Stats")
    h = output.get_actor("PhaseSpace")
    print(stats)
    #
    f_phsp = uproot.open(paths.output / "test065_output_data.root")
    arr = f_phsp["PhaseSpace"].arrays()
    print("Number of detected events :", len(arr))
    print("Number of expected events :", nb_part, "+- 3*" + str(int(np.round(np.sqrt(nb_part)))))

    is_ok = validation_test(nb_part,len(arr))
    gate.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test064")
    output_path = paths.output

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    # sim.running_verbose_level = gate.EVENT
    sim.number_of_threads = 2
    sim.random_seed = 987654321
    sim.output_dir = output_path

    # units
    m = gate.g4_units.m
    km = gate.g4_units.km
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    gcm3 = gate.g4_units["g/cm3"]

    #  adapt world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_Galactic"

    # nb of particles
    n = 2000

    # source1
    source1 = sim.add_source("GenericSource", "photon_source")
    source1.particle = "gamma"
    source1.position.type = "box"
    source1.position.size = [1 * cm, 1 * cm, 1 * cm]
    source1.position.translation = [10 * cm, 0 * cm, 3 * cm]
    source1.direction.type = "momentum"
    source1.direction.momentum = [0, 0, -1]
    source1.energy.type = "mono"
    source1.energy.mono = 1 * MeV
    source1.n = n / sim.number_of_threads

    # source2
    source2 = sim.add_source("GenericSource", "photon_source_2")
    source2.particle = "gamma"
    source2.position.type = "point"
    source2.position.size = [1 * cm, 1 * cm, 1 * cm]
    source2.position.translation = [-10 * cm, 0 * cm, -3 * cm]
    source2.direction.type = "momentum"
    source2.direction.momentum = [0, 0, 1]
    source2.energy.type = "mono"
    source2.energy.mono = 1 * MeV
    source2.n = n / sim.number_of_threads

    # stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # add phase space plan
    phsp_plane = sim.add_volume("Box", "phase_space_plane")
    phsp_plane.mother = world
    phsp_plane.material = "G4_Galactic"
    phsp_plane.size = [1 * m, 1 * m, 1 * nm]
    phsp_plane.translation = [0, 0, 0]
    phsp_plane.color = [1, 0, 0, 1]  # red

    # PhaseSpace Actor
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = phsp_plane
    phsp.attributes = ["EventID"]
    phsp.output_filename = "test064.root"

    # kill actor volume
    kill_plane = sim.add_volume("Box", "Kill_plane")
    kill_plane.mother = world
    kill_plane.material = "G4_Galactic"
    kill_plane.size = [10 * cm, 10 * cm, 1 * nm]
    kill_plane.translation = [-10 * cm, 0, -2 * cm]
    kill_plane.color = [0, 1, 0, 1]  # green

    # kill actor
    kill_actor = sim.add_actor("KillActor", "KillAct")
    kill_actor.attached_to = kill_plane

    # Physic list and cuts
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * mm
    sim.physics_manager.global_production_cuts.positron = 1 * mm

    # go !
    sim.run()

    # print results
    print(stats)

    f_phsp = uproot.open(phsp.get_output_path())
    arr = f_phsp["PhaseSpace"].arrays()
    print("Number of detected events :", len(arr))
    print("Number of expected events :", n)
    # EventID = arr[0]

    # Nb of kill
    nk = kill_actor.number_of_killed_particles
    print(f"Number of kills = {nk}")

    is_ok = len(arr) == n
    is_ok = (nk == n) and is_ok
    utility.test_ok(is_ok)

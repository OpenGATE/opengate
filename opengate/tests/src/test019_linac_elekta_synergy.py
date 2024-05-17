#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.linacs.elektasynergy as synergy
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import numpy as np

if __name__ == "__main__":
    # paths
    paths = utility.get_default_test_paths(__file__, output_folder="test019_linac")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.random_seed = 12345678
    sim.check_volumes_overlap = True
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm

    # world
    world = sim.world
    world.size = [2 * m, 2 * m, 3 * m]
    world.material = "G4_AIR"

    # add a linac
    linac = synergy.add_linac(sim, "synergy")
    linac.translation += np.array([50 * mm, 19 * mm, 17 * mm])
    linac.rotation = Rotation.from_euler("ZY", [38, 29], degrees=True).as_matrix()

    # add linac e- source
    source = synergy.add_electron_source(sim, linac.name, linac.rotation)
    source.n = 1e4 / sim.number_of_threads
    if sim.visu:
        source.n = 2

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)
    synergy.enable_brem_splitting(sim, linac.name, splitting_factor=100)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # add phase space
    plane = synergy.add_phase_space_plane(sim, linac.name, 299.99 * mm)
    plane.rmax = 70 * mm
    phsp = synergy.add_phase_space(sim, plane.name)
    phsp.output_filename = "phsp_synergy.root"
    print(f"Output filename {phsp.get_output_path()}")

    # start simulation
    sim.run()

    # print results
    print(stats)

    # compare root
    br = "synergy_phsp_plane_phsp"
    print()
    root_ref = paths.output_ref / "phsp_synergy_no_tr_no_rot.root"
    keys = ["KineticEnergy", "PrePositionLocal_X", "PrePositionLocal_Y"]
    tols = [0.03, 1.8, 1.8]
    is_ok = utility.compare_root3(
        root_ref,
        phsp.get_output_path(),
        br,
        br,
        keys,
        keys,
        tols,
        None,
        None,
        paths.output / "phsp_synergy1.png",
        hits_tol=7,
    )

    print()
    root_ref = paths.output_ref / "phsp_synergy_tr_no_rot.root"
    keys = ["KineticEnergy", "PrePositionLocal_X", "PrePositionLocal_Y"]
    tols = [0.03, 1.8, 1.8]
    is_ok = (
        utility.compare_root3(
            root_ref,
            phsp.get_output_path(),
            br,
            br,
            keys,
            keys,
            tols,
            None,
            None,
            paths.output / "phsp_synergy2.png",
            hits_tol=7,
        )
        and is_ok
    )

    print()
    root_ref = paths.output_ref / "phsp_synergy_tr_rot.root"
    keys = [
        "KineticEnergy",
        "PrePosition_X",
        "PrePosition_Y",
        "PrePositionLocal_X",
        "PrePositionLocal_Y",
    ]
    tols = [0.03, 1.8, 1.8, 1.8, 1.8]
    is_ok = (
        utility.compare_root3(
            root_ref,
            phsp.get_output_path(),
            br,
            br,
            keys,
            keys,
            tols,
            None,
            None,
            paths.output / "phsp_synergy3.png",
            hits_tol=7,
        )
        and is_ok
    )
    # end
    utility.test_ok(is_ok)

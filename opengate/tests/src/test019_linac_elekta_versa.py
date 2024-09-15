#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.linacs.elektaversa as versa
from opengate.tests import utility

if __name__ == "__main__":
    # paths
    paths = utility.get_default_test_paths(__file__, output_folder="test019_linac")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.output_dir = paths.output  # FIXME (not yet)
    sim.random_seed = 123456789
    sim.check_volumes_overlap = True
    sim.output_dir = paths.output
    sim.progress_bar = True

    # units
    nm = gate.g4_units.nm
    m = gate.g4_units.m
    mm = gate.g4_units.mm

    # world
    world = sim.world
    world.size = [4 * m, 4 * m, 4 * m]
    world.material = "G4_AIR"

    # add a linac
    linac = versa.add_linac(sim, "versa")
    translation = [50 * mm, 12 * mm, 29 * mm]
    versa.translation_from_sad(sim, linac.name, translation, sad=1000)
    versa.rotation_around_user_point(
        sim, linac.name, "ZY", [38, 28], [224 * mm, -47 * mm, 456 * mm]
    )

    # add linac e- source
    source = versa.add_electron_source(sim, linac.name)
    source.n = 8e4 / sim.number_of_threads
    if sim.visu:
        source.n = 200

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)
    versa.enable_brem_splitting(sim, linac.name, splitting_factor=10)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # add phase space
    plane = versa.add_phase_space_plane(sim, linac.name, linac.size[2] - 1 * nm)
    phsp = versa.add_phase_space(sim, plane.name)
    phsp.output_filename = "phsp_versa.root"

    # start simulation
    sim.run()

    # print results
    print(stats)

    # compare root
    br = "versa_phsp_plane_phsp"
    root_ref = paths.output_ref / "phsp_versa_no_tr_no_rot.root"
    keys = ["KineticEnergy", "PrePositionLocal_X", "PrePositionLocal_Y"]
    tols = [0.1, 2.5, 2.5]
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
        paths.output / "phsp_versa1.png",
        hits_tol=80,
    )

    root_ref = paths.output_ref / "phsp_versa_tr_no_rot.root"
    keys = ["KineticEnergy", "PrePositionLocal_X", "PrePositionLocal_Y"]
    tols = [0.1, 2.5, 2.5]
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
            paths.output / "phsp_versa2.png",
            hits_tol=80,
        )
        and is_ok
    )

    root_ref = paths.output_ref / "phsp_versa_tr_rot.root"
    keys = [
        "KineticEnergy",
        "PrePosition_X",
        "PrePosition_Y",
        "PrePositionLocal_X",
        "PrePositionLocal_Y",
    ]
    tols = [0.1, 2.5, 2.5, 2.5, 2.5]
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
            paths.output / "phsp_versa3.png",
            hits_tol=80,
        )
        and is_ok
    )
    # end
    utility.test_ok(is_ok)

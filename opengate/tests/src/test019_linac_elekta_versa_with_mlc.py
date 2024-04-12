#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.linacs.elektaversa as versa
from opengate.tests import utility
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    # paths
    paths = utility.get_default_test_paths(__file__, output_folder="test019_linac")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = True
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.output_dir = paths.output  # FIXME (not yet)
    # sim.random_seed = 123456789 # FIXME
    sim.check_volumes_overlap = True

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm

    # world
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_AIR"

    # add a linac
    linac = versa.add_linac(sim, "versa", None)

    # FIXME TODO : add jaws
    # jaws = versa.add_jaws(sim, linac.name, "left")

    # FIXME TODO MLC :
    # mlc = versa.add_mlc(sim, "versa")
    # versa.mlc_field_rectangular(sim, mlc, 10*cm, 15*cm)
    # versa.mlc_field(sim, mlc, left_leaf_positions, right_leaf_positions)

    # add linac e- source
    source = versa.add_electron_source(sim, linac.name, linac.rotation)
    source.n = 5e4 / sim.number_of_threads
    if sim.visu:
        source.n = 200

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)
    versa.enable_brem_splitting(sim, linac.name, splitting_factor=10)

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True

    # add phase space
    """plane = versa.add_phase_space_plane(sim, linac.name)
    phsp = versa.add_phase_space(sim, plane.name)
    phsp.output = paths.output / "phsp_versa_mlc.root"""

    # start simulation
    sim.run()

    # print results
    stats = sim.output.get_actor(s.name)
    print(stats)

    # end
    is_ok = False
    utility.test_ok(is_ok)

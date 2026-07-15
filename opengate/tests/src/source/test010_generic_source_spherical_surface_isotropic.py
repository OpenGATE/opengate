#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

import gatetools
import numpy as np


def run_simulation(paths):
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    deg = gate.g4_units.deg

    # geometry
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    sphere_center_1 = [5 * cm, 7 * cm, -9 * cm]
    sphere_center_2 = [-8 * cm, -6 * cm, 5 * cm]
    sphere_center_3 = [0 * cm, 0 * cm, 0 * cm]

    sphere_1 = sim.add_volume("Sphere", "probe_sphere_1")
    sphere_1.rmax = 5 * cm
    sphere_1.translation = sphere_center_1
    sphere_1.material = "G4_Galactic"

    sphere_2 = sim.add_volume("Sphere", "probe_sphere_2")
    sphere_2.rmax = 5 * cm
    sphere_2.translation = sphere_center_2
    sphere_2.material = "G4_Galactic"

    sphere_3 = sim.add_volume("Sphere", "probe_sphere_3")
    sphere_3.rmax = 5 * cm
    sphere_3.translation = sphere_center_3
    sphere_3.material = "G4_Galactic"

    # source
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.n = 1e5
    source.position.type = "surface_sphere"
    source.position.radius = 19.9 * cm
    source.position.translation = [0 * cm, 0 * cm, 0 * cm]
    source.direction.type = "cos"
    source.direction.theta = [0 * deg, 90 * deg]
    source.direction.phi = [0 * deg, 360 * deg]
    source.energy.type = "mono"
    source.energy.mono = 100 * keV

    # actors
    phsp_1 = sim.add_actor("PhaseSpaceActor", "phsp_1")
    phsp_1.attributes = ["PrePosition", "PreDirection"]
    phsp_1.attached_to = sphere_1
    phsp_1.output_filename = (
        "test010_generic_source_spherical_surface_isotropic_phsp_1.root"
    )

    phsp_2 = sim.add_actor("PhaseSpaceActor", "phsp_2")
    phsp_2.attributes = ["PrePosition", "PreDirection"]
    phsp_2.attached_to = sphere_2
    phsp_2.output_filename = (
        "test010_generic_source_spherical_surface_isotropic_phsp_2.root"
    )

    phsp_3 = sim.add_actor("PhaseSpaceActor", "phsp_3")
    phsp_3.attributes = ["PrePosition", "PreDirection"]
    phsp_3.attached_to = sphere_3
    phsp_3.output_filename = (
        "test010_generic_source_spherical_surface_isotropic_phsp_3.root"
    )

    # start simulation
    sim.run()

    # analyze results
    #
    # get positions and directions when particles entered the probe spheres
    poss_1, dirs_1 = root_load_pos_and_dir(str(phsp_1.get_output_path()))
    poss_2, dirs_2 = root_load_pos_and_dir(str(phsp_2.get_output_path()))
    poss_3, dirs_3 = root_load_pos_and_dir(str(phsp_3.get_output_path()))

    # Test if all probe spheres get the same expected (empirically only) amount of photons.
    # We can be quite tolerant (10%), as switching to different source configurations (e.g., direction.type "iso")
    # should lead to very different results.
    assert np.isclose(len(poss_1), 6300, rtol=0.1)
    assert np.isclose(len(poss_2), 6300, rtol=0.1)
    assert np.isclose(len(poss_3), 6300, rtol=0.1)

    # compute the relative vector between sphere center and position
    r_1 = poss_1 - sphere_center_1
    r_2 = poss_2 - sphere_center_2
    r_3 = poss_3 - sphere_center_3

    # compute distance of position from sphere center – this should equal the sphere radius by construction
    r_norm_1 = np.linalg.norm(r_1, axis=1)
    r_norm_2 = np.linalg.norm(r_2, axis=1)
    r_norm_3 = np.linalg.norm(r_3, axis=1)
    assert np.allclose(r_norm_1, 5 * cm, rtol=1e-3)
    assert np.allclose(r_norm_2, 5 * cm, rtol=1e-3)
    assert np.allclose(r_norm_3, 5 * cm, rtol=1e-3)

    # compute normal vectors
    norm_1 = r_1 / r_norm_1[:, None]
    norm_2 = r_2 / r_norm_2[:, None]
    norm_3 = r_3 / r_norm_3[:, None]

    # calculate mu = dir * (-norm)
    mu_1 = -np.sum(dirs_1 * norm_1, axis=1)
    mu_2 = -np.sum(dirs_2 * norm_2, axis=1)
    mu_3 = -np.sum(dirs_3 * norm_3, axis=1)

    # mu should follow cosine law
    assert abs(mu_1.mean() - 2 / 3) < 0.05
    assert abs(mu_2.mean() - 2 / 3) < 0.05
    assert abs(mu_3.mean() - 2 / 3) < 0.05
    assert abs(mu_1.var() - 1 / 18) < 0.05
    assert abs(mu_2.var() - 1 / 18) < 0.05
    assert abs(mu_3.var() - 1 / 18) < 0.05


def root_load_pos_and_dir(root_file: str):
    data_ref, keys_ref, _ = gatetools.phsp.load(root_file)

    index_pos_x = keys_ref.index("PrePosition_X")
    index_pos_y = keys_ref.index("PrePosition_Y")
    index_pos_z = keys_ref.index("PrePosition_Z")
    index_dir_x = keys_ref.index("PreDirection_X")
    index_dir_y = keys_ref.index("PreDirection_Y")
    index_dir_z = keys_ref.index("PreDirection_Z")
    pos_x = [x[index_pos_x] for x in data_ref]
    pos_y = [x[index_pos_y] for x in data_ref]
    pos_z = [x[index_pos_z] for x in data_ref]
    dir_x = [x[index_dir_x] for x in data_ref]
    dir_y = [x[index_dir_y] for x in data_ref]
    dir_z = [x[index_dir_z] for x in data_ref]
    poss = np.stack((pos_x, pos_y, pos_z), axis=1)
    dirs = np.stack((dir_x, dir_y, dir_z), axis=1)

    return poss, dirs


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__,
        "test010_generic_source_spherical_surface_isotropic",
        output_folder="test010",
    )

    run_simulation(paths)

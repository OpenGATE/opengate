#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.linacs.elektaversa as versa
import scipy.optimize
from opengate.tests import utility
import numpy as np
import uproot
import matplotlib.pyplot as plt


def is_ok_test019(rootfile, x_field, y_field, tol=0.15):
    x = rootfile["PrePosition_X"][rootfile["ParticleName"] == "alpha"]
    y = rootfile["PrePosition_Y"][rootfile["ParticleName"] == "alpha"]

    hist_x_pos = plt.hist(
        x, bins=50, density=True, range=[-1.5 * x_field / 2, 1.5 * x_field / 2]
    )
    x_hist_x_pos = hist_x_pos[1][:-1] + 0.5 * (hist_x_pos[1][1] - hist_x_pos[1][0])
    median_hist_x_pos = np.median(hist_x_pos[0][hist_x_pos[0] > 0])
    y_hist_x_pos = hist_x_pos[0]
    fwhm_x_pos = (
        -x_hist_x_pos[np.where(hist_x_pos[0] > median_hist_x_pos / 3)[0]][0]
        + x_hist_x_pos[np.where(hist_x_pos[0] > median_hist_x_pos / 3)[0]][-1]
    )

    hist_y_pos = plt.hist(
        y, bins=40, density=True, range=[-1.5 * y_field / 2, 1.5 * y_field / 2]
    )
    x_hist_y_pos = hist_y_pos[1][:-1] + 0.5 * (hist_y_pos[1][1] - hist_y_pos[1][0])
    median_hist_y_pos = np.median(hist_y_pos[0][hist_y_pos[0] > 0])

    fwhm_y_pos = (
        -x_hist_y_pos[np.where(hist_y_pos[0] > median_hist_y_pos / 3)[0]][0]
        + x_hist_y_pos[np.where(hist_y_pos[0] > median_hist_y_pos / 3)[0]][-1]
    )
    fwhm_y_pos += x_hist_y_pos[2] - x_hist_y_pos[0]
    # a trick to correct the fact that the jaws aperture for alpha is a bit underestimated

    bool_x_pos = (fwhm_x_pos > x_field * (1 - tol)) & (fwhm_x_pos < x_field * (1 + tol))
    bool_y_pos = (fwhm_y_pos > y_field * (1 - tol)) & (fwhm_y_pos < y_field * (1 + tol))

    print("field dimension on the x-axis position :", x_field, "mm")
    print("FWHM measured for the x-axis beam :", fwhm_x_pos, "mm")
    print("field dimension on the y-axis position :", y_field, "mm")
    print("FWHM measured for the y-axis beam :", fwhm_y_pos, "mm")
    return bool_x_pos and bool_y_pos


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
    sim.random_seed = 123456789
    sim.check_volumes_overlap = True
    sim.output_dir = paths.output

    # unit
    nm = gate.g4_units.nm
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV

    # world
    world = sim.world
    world.size = [2 * m, 2 * m, 2.2 * m]
    world.material = "G4_Galactic"
    a = np.array([0])

    # linac (empty)
    versa.add_linac_materials(sim)
    sad = 1000 * mm
    linac = versa.add_empty_linac_box(sim, "linac_box", sad)
    linac.material = "G4_Galactic"

    # jaws

    jaws = versa.add_jaws(sim, linac.name)

    # mlc
    mlc = versa.add_mlc(sim, linac.name)
    x_field = np.random.randint(10, 20, 1)[0] * cm
    y_field = np.random.randint(10, 20, 1)[0] * cm

    print("field: ", x_field, y_field)
    versa.set_rectangular_field(mlc, jaws, x_field, y_field, sad)

    mlc_box = sim.volume_manager.get_volume(f"linac_box_mlc")
    mlc_box.material = "G4_Galactic"

    # add alpha source
    source = sim.add_source("GenericSource", f"alpha_source")
    source.particle = "alpha"
    source.attached_to = linac.name
    z_linac = linac.size[2]
    source.energy.type = "gauss"
    source.energy.mono = 1 * MeV
    source.position.type = "disc"
    source.position.sigma_x = 0.468 * mm
    source.position.sigma_y = 0.468 * mm
    source.position.translation = [0, 0, z_linac / 2 - 5.6 * mm]
    source.direction.type = "iso"
    source.n = 5e5 / sim.number_of_threads
    if sim.visu:
        source.n = 100

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1000 * m)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # add phase space
    plane = sim.add_volume("Box", "phsp_plane")
    plane.mother = world
    plane.material = "G4_Galactic"
    plane.size = [0.5 * m, 0.5 * m, 1 * nm]
    plane.color = [1, 0, 0, 1]  # red

    phsp = sim.add_actor("PhaseSpaceActor", f"phsp")
    phsp.attached_to = plane.name
    phsp.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PrePositionLocal",
        "PreDirection",
        "PreDirectionLocal",
        "PDGCode",
        "ParticleName",
    ]
    phsp.output_filename = "phsp_versa_mlc.root"

    # start simulation
    sim.run()

    # print results
    print(stats)

    # end
    with uproot.open(phsp.get_output_path()) as f_phsp:
        arr = f_phsp["phsp"].arrays()

    is_ok = is_ok_test019(arr, x_field, y_field)
    utility.test_ok(is_ok)

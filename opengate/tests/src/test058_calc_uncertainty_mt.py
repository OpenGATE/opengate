#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import uproot
import pathlib
import numpy as np
import itk
import opengate as gate
from opengate.tests import utility


def assert_uncertainty(
    img_E,
    img_err_E,
    nb_part,
    mean_E,
    std_E,
    tab_E,
    tol_th=0.075,
    tol_phsp=0.005,
    is_ok=True,
):
    val_E_img = img_E[0, 0, 0]
    val_err_E_img = round(val_E_img * img_err_E[0, 0, 0], 3)
    val_E_img = round(val_E_img, 2)
    phsp_sum_squared_E = np.sum(tab_E**2)
    phsp_sum_E = np.sum(tab_E)
    phsp_unc = phsp_sum_squared_E / nb_part - (phsp_sum_E / nb_part) ** 2
    phsp_unc = (1 / (nb_part - 1)) * phsp_unc
    phsp_unc = np.sqrt(phsp_unc) * nb_part
    print(
        "Energy deposited in the voxel for "
        + str(round(nb_part))
        + " particles : "
        + str(val_E_img)
        + " MeV"
    )

    print(
        "Energy recorded in the phase space for "
        + str(round(nb_part))
        + " particles : "
        + str(round(phsp_sum_E, 2))
        + " MeV"
    )
    print("Theoretical deposited energy : " + str(mean_E * nb_part) + " MeV")
    print(
        "Standard error on the deposited energy in the voxel for "
        + str(round(nb_part))
        + " particles : "
        + str(val_err_E_img)
        + " MeV"
    )

    print(
        "Standard error on the phase space energy deposition "
        + str(round(nb_part))
        + " particles : "
        + str(round(phsp_unc, 3))
        + " MeV"
    )
    print(
        "Theoretical standard error on deposited energy : "
        + str(round(std_E * np.sqrt(nb_part), 3))
        + " MeV"
    )
    print("Tolerance on the theory comparison: " + str(100 * tol_th) + " %")
    print("Tolerance on the phase space comparison: " + str(100 * tol_phsp) + " %")

    var_err_E_th = abs((val_err_E_img - (std_E * np.sqrt(nb_part)))) / (
        std_E * np.sqrt(nb_part)
    )

    var_err_E_phsp = abs((phsp_unc - val_err_E_img)) / (val_err_E_img)

    print(
        "Standard error variation with respect to theory [%] : "
        + str(100 * round(var_err_E_th, 3))
    )
    print(
        "Standard error variation with respect to phase space recording [%] : "
        + str(100 * round(var_err_E_phsp, 3))
    )
    if var_err_E_th > tol_th or var_err_E_phsp > tol_phsp:
        is_ok = False

    return is_ok


if __name__ == "__main__":
    current_path = pathlib.Path(__file__).parent.resolve()
    output_path = current_path / ".." / "output"

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    # ui.visu_type = "vrml"
    ui.check_volumes_overlap = False
    # ui.running_verbose_level = gate.EVENT
    ui.number_of_threads = 5
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
    gcm3 = gate.g4_units.g_cm3

    #  adapt world size
    world = sim.world
    world.size = [200 * m, 200 * m, 201 * m]

    block_size = [200 * m, 200 * m, 200 * m]

    # Tungsten block
    sim.add_material_weights(
        "Tungsten",
        ["W"],
        [1],
        19.3 * gcm3,
    )
    t_block = sim.add_volume("Box", "T_block")
    t_block.mother = world.name
    t_block.material = "Tungsten"
    t_block.size = block_size
    t_block.translation = [0 * mm, 0 * mm, -0.5 * m]
    t_block.color = [0, 1, 0, 1]
    t_block.mother = world.name

    # source

    nb_part = 1000 / ui.number_of_threads
    std_dev_E = 10 * keV
    mean_E = 100 * keV
    source = sim.add_source("GenericSource", "photon_source")
    source.particle = "gamma"
    source.n = nb_part
    source.position.type = "box"
    source.position.size = [3 * cm, 3 * cm, 0 * cm]
    source.direction.type = "momentum"
    source.mother = world.name
    source.direction.momentum = [0, 0, -1]
    source.energy.type = "gauss"
    source.energy.mono = mean_E
    source.energy.sigma_gauss = std_dev_E

    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    # s.track_types_flag = True

    # add phase space plan

    phsp = sim.add_volume("Box", "phase_space_plane")
    phsp.mother = world.name
    phsp.material = "G4_AIR"
    phsp.size = [200 * m, 200 * m, 1 * nm]
    phsp.translation = [0 * m, 0 * m, 0 * m]
    phsp.color = [1, 0, 0, 1]  # red

    # PhaseSpace Actor
    Phsp_act = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    Phsp_act.mother = phsp.name
    Phsp_act.attributes = [
        "KineticEnergy",
        "EventID",
        "ThreadID",
    ]
    Phsp_act.output = output_path / "test058_MT.root"
    Phsp_act.debug = False

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = output_path / "test058_MT.mhd"
    dose.mother = t_block.name
    dose.size = [1, 1, 1]
    dose.spacing = block_size
    dose.img_coord_system = False
    dose.uncertainty = True
    dose.translation = [0 * mm, 0 * mm, -0.5 * m]
    dose.hit_type = "random"

    # Physic list and cuts
    p = sim.get_physics_user_info()
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 1 * km
    sim.physics_manager.global_production_cuts.electron = 1 * km
    sim.physics_manager.global_production_cuts.positron = 1 * km

    sim.run()

    # print results
    stats = sim.output.get_actor("Stats")
    h = sim.output.get_actor("PhaseSpace")
    print(stats)

    # Open images for comparison

    img_E = itk.imread(output_path / "test058_MT.mhd")
    array_E = itk.GetArrayFromImage(img_E)
    err_img_E = itk.imread(output_path / "test058_MT_uncertainty.mhd")
    err_array_E = itk.GetArrayFromImage(err_img_E)

    f_phsp = uproot.open(output_path / "test058_MT.root")
    arr_phsp = f_phsp["PhaseSpace"]
    keys_data = arr_phsp.keys(filter_typename="double")
    E = f_phsp["PhaseSpace;1/KineticEnergy"]
    Ephoton = E.array()

    is_ok = assert_uncertainty(
        array_E, err_array_E, nb_part * ui.number_of_threads, mean_E, std_dev_E, Ephoton
    )
    utility.test_ok(is_ok)

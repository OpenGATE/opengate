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

    nb_part = int(nb_part)
    print(f"Energy deposited in the voxel for {nb_part} particles : {val_E_img} MeV")
    print(
        f"Energy recorded in the phase space for {nb_part} particles : {round(phsp_sum_E, 2)} MeV"
    )
    print(f"Theoretical deposited energy : {mean_E * nb_part} MeV")
    print(
        f"Standard error on the deposited energy in the voxel for {nb_part} particles : {val_err_E_img} MeV"
    )
    print(
        f"Standard error on the phase space energy deposition {nb_part} particles : {round(phsp_unc, 3)} MeV"
    )

    tstd_e = std_E * np.sqrt(nb_part)
    print(f"Theoretical standard error on deposited energy : {round(tstd_e, 3)} MeV")

    print()
    print(f"Tolerance on the theory comparison: {100 * tol_th}  %")
    print(f"Tolerance on the phase space comparison: {100 * tol_phsp} %")

    var_err_E_th = abs((val_err_E_img - tstd_e)) / tstd_e
    var_err_E_phsp = abs((phsp_unc - val_err_E_img)) / val_err_E_img

    print(
        f"Standard error variation with respect to theory:  {100 * round(var_err_E_th, 3)} %"
    )
    print(
        f"Standard error variation with respect to phase space recording: {100 * round(var_err_E_phsp, 3)} %"
    )

    print(var_err_E_th, var_err_E_phsp)

    if var_err_E_th > tol_th or var_err_E_phsp > tol_phsp:
        is_ok = False

    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test058")
    current_path = pathlib.Path(__file__).parent.resolve()
    output_path = paths.output

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    # sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    # sim.running_verbose_level = gate.EVENT
    sim.number_of_threads = 5
    sim.random_seed = 12365445
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
    gcm3 = gate.g4_units.g_cm3

    #  adapt world size
    world = sim.world
    world.size = [200 * m, 200 * m, 201 * m]

    block_size = [200 * m, 200 * m, 200 * m]

    # Tungsten block
    sim.volume_manager.material_database.add_material_weights(
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
    nb_part = 1000 / sim.number_of_threads
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

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
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
    Phsp_act.attached_to = phsp.name
    Phsp_act.attributes = [
        "KineticEnergy",
        "EventID",
        "ThreadID",
    ]
    Phsp_act.output_filename = "test058_MT.root"
    Phsp_act.debug = False
    Phsp_act.steps_to_store = "exiting first"

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test058_MT.mhd"
    dose.attached_to = t_block.name
    dose.size = [1, 1, 1]
    dose.spacing = block_size
    dose.edep_uncertainty.active = True
    dose.translation = [0 * mm, 0 * mm, -0.5 * m]
    dose.hit_type = "random"

    # Physic list and cuts
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 1 * km
    sim.physics_manager.global_production_cuts.electron = 1 * km
    sim.physics_manager.global_production_cuts.positron = 1 * km

    sim.run()

    # print results
    print(stats)

    # Open images for comparison

    img_E = itk.imread(dose.get_output_path("edep"))
    array_E = itk.GetArrayFromImage(img_E)
    err_img_E = itk.imread(dose.get_output_path("edep_uncertainty"))
    err_array_E = itk.GetArrayFromImage(err_img_E)

    f_phsp = uproot.open(output_path / "test058_MT.root")
    arr_phsp = f_phsp["PhaseSpace"]
    keys_data = arr_phsp.keys(filter_typename="double")
    E = f_phsp["PhaseSpace;1/KineticEnergy"]
    Ephoton = E.array()

    is_ok = assert_uncertainty(
        array_E,
        err_array_E,
        nb_part * sim.number_of_threads,
        mean_E,
        std_dev_E,
        Ephoton,
    )
    utility.test_ok(is_ok)

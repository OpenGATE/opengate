#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import uproot
from opengate.tests import utility
import opengate as gate
from opengate.contrib.beamlines.ionbeamline import BeamlineModel
from opengate.contrib.tps.ionbeamtherapy import spots_info_from_txt, TreatmentPlanSource
from scipy.spatial.transform import Rotation
import itk
import matplotlib.pyplot as plt
import os
import numpy as np


def calculate_mean_unc(edep_arr, unc_arr, edep_thresh_rel=0.7):
    edep_max = np.amax(edep_arr)
    mask = edep_arr > edep_max * edep_thresh_rel
    unc_used = unc_arr[mask]
    unc_mean = np.mean(unc_used)

    return unc_mean


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
    paths = utility.get_default_test_paths(__file__, "gate_test044_pbs")
    output_path = paths.output / "output_test059_rtp"
    ref_path = paths.output_ref / "test059_ref"

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 123654789
    ui.random_engine = "MersenneTwister"
    ui.number_of_threads = 1

    # units
    km = gate.g4_units.km
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    um = gate.g4_units.um
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm
    deg = gate.g4_units.deg
    mrad = gate.g4_units.mrad

    # add a material database
    sim.add_material_database(paths.gate_data / "HFMaterials2014.db")

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]

    ## FIRST DETECTOR ##
    # box
    # translation and rotation like in the Gate macro
    box1 = sim.add_volume("Box", "box1")
    box1.size = [200 * mm, 200 * mm, 1050 * mm]
    # box1.translation = [0 * cm, 0 * cm, 52.5 * cm]
    # box1.rotation = Rotation.from_euler('y',-90,degrees=True).as_matrix()
    box1.translation = [0 * cm, 0 * cm, 52.5 * cm]
    box1.material = "Vacuum"
    box1.color = [0, 0, 1, 1]

    # phantoms
    m = Rotation.identity().as_matrix()

    phantom1_s1 = sim.add_volume("Box", "phantom1_s1")
    phantom1_s1.mother = "box1"
    phantom1_s1.size = [100 * mm, 100 * mm, 50 * mm]
    phantom1_s1.translation = [-50 * mm, 0 * mm, -500 * mm]
    phantom1_s1.rotation = m
    phantom1_s1.material = "G4_WATER"
    phantom1_s1.color = [1, 0, 1, 1]

    phantom1_s2 = sim.add_volume("Box", "phantom1_s2")
    phantom1_s2.mother = "box1"
    phantom1_s2.size = [100 * mm, 100 * mm, 50 * mm]
    phantom1_s2.translation = [50 * mm, 0 * mm, -500 * mm]
    phantom1_s2.rotation = m
    phantom1_s2.material = "G4_WATER"
    phantom1_s2.color = [1, 0, 1, 1]

    # add dose actor
    dose1_s1 = sim.add_actor("DoseActor", "edep_11")
    filename = "phantom1_s1.mhd"
    dose1_s1.output = output_path / filename
    dose1_s1.mother = "phantom1_s1"
    dose1_s1.size = [25, 25, 1]
    dose1_s1.spacing = [4.0, 4.0, 50.0]
    dose1_s1.hit_type = "random"
    dose1_s1.uncertainty = True
    # dose1_s1.ste_of_mean = True

    # add dose actor
    dose1_s2 = sim.add_actor("DoseActor", "edep_12")
    filename = "phantom1_s2.mhd"
    dose1_s2.output = output_path / filename
    dose1_s2.mother = "phantom1_s2"
    dose1_s2.size = [25, 25, 1]
    dose1_s2.spacing = [4.0, 4.0, 50.0]
    dose1_s2.hit_type = "random"
    dose1_s2.uncertainty = True
    # # PhaseSpace Actor
    # Phsp_act = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    # Phsp_act.mother = phantom1_s2.name
    # Phsp_act.attributes = [
    #     "KineticEnergy",
    #     "EventID",
    #     "ThreadID",
    # ]
    # Phsp_act.output = output_path / "test058_MT.root"
    # Phsp_act.debug = False

    ## SECOND DETECTOR ##
    # box
    # translation and rotation like in the Gate macro
    box2 = sim.add_volume("Box", "box2")
    box2.size = [200 * mm, 200 * mm, 1050 * mm]
    # box2.rotation = Rotation.from_euler('y',90,degrees=True).as_matrix()
    box2.translation = [40 * cm, 0 * cm, 52.5 * cm]
    # box2.translation = [-52.5* cm, 0 * cm, 40 * cm]
    box2.material = "Vacuum"
    box2.color = [0, 0, 1, 1]

    # phantoms
    m = Rotation.identity().as_matrix()

    phantom2_s1 = sim.add_volume("Box", "phantom2_s1")
    phantom2_s1.mother = "box2"
    phantom2_s1.size = [100 * mm, 100 * mm, 50 * mm]
    phantom2_s1.translation = [-50 * mm, 0 * mm, -500 * mm]
    phantom2_s1.rotation = m
    phantom2_s1.material = "G4_WATER"
    phantom2_s1.color = [1, 0, 1, 1]

    phantom2_s2 = sim.add_volume("Box", "phantom2_s2")
    phantom2_s2.mother = "box2"
    phantom2_s2.size = [100 * mm, 100 * mm, 50 * mm]
    phantom2_s2.translation = [50 * mm, 0 * mm, -500 * mm]
    phantom2_s2.rotation = m
    phantom2_s2.material = "G4_WATER"
    phantom2_s2.color = [1, 0, 1, 1]

    # add dose actor
    dose2_s1 = sim.add_actor("DoseActor", "edep_21")
    filename = "phantom2_s1.mhd"
    dose2_s1.output = output_path / filename
    dose2_s1.mother = "phantom2_s1"
    dose2_s1.size = [25, 25, 1]
    dose2_s1.spacing = [4.0, 4.0, 50.0]
    dose2_s1.hit_type = "random"
    dose2_s1.uncertainty = True

    dose2_s2 = sim.add_actor("DoseActor", "edep_22")
    filename = "phantom2_s2.mhd"
    dose2_s2.output = output_path / filename
    dose2_s2.mother = "phantom2_s2"
    dose2_s2.size = [25, 25, 1]
    dose2_s2.spacing = [4.0, 4.0, 50.0]
    dose2_s2.hit_type = "random"
    dose2_s2.uncertainty = True

    ## TPS SOURCE ##
    # beamline model
    beamline = BeamlineModel()
    beamline.name = None
    beamline.radiation_types = "proton"

    # polinomial coefficients
    beamline.energy_mean_coeffs = [1, 0]
    beamline.energy_spread_coeffs = [0.4417036946562556]
    beamline.sigma_x_coeffs = [2.3335754]
    beamline.theta_x_coeffs = [2.3335754e-3]
    beamline.epsilon_x_coeffs = [0.00078728e-3]
    beamline.sigma_y_coeffs = [1.96433431]
    beamline.theta_y_coeffs = [0.00079118e-3]
    beamline.epsilon_y_coeffs = [0.00249161e-3]

    # tps
    nSim = 40000  # particles to simulate per beam
    print("--- Flat spots distribution ---")
    spots, ntot, energies, G = spots_info_from_txt(
        ref_path / "TreatmentPlan2Spots_flat_gen_test.txt", "proton", beam_nr=1
    )
    tps_flat = TreatmentPlanSource("flat", sim)
    tps_flat.set_beamline_model(beamline)
    tps_flat.set_particles_to_simulate(nSim)
    tps_flat.set_spots(spots)
    tps_flat.rotation = Rotation.from_euler("x", 90, degrees=True)
    tps_flat.translation = [0 * cm, 0 * cm, -30 * cm]
    tps_flat.initialize_tpsource(flat_generation=True)
    print(f"Tot sim particles flat: {tps_flat.actual_sim_particles}")

    print("--- Proportional spots distribution ---")
    spots, ntot, energies, G = spots_info_from_txt(
        ref_path / "TreatmentPlan2Spots_flat_gen_test.txt", "proton", beam_nr=1
    )
    tps_not_flat = TreatmentPlanSource("not flat", sim)
    tps_not_flat.set_beamline_model(beamline)
    tps_not_flat.set_particles_to_simulate(nSim)
    tps_not_flat.set_spots(spots)
    tps_not_flat.rotation = Rotation.from_euler("x", 90, degrees=True)
    tps_not_flat.translation = [40 * cm, 0 * cm, 0 * cm]
    tps_not_flat.initialize_tpsource(flat_generation=False)
    print(f"Tot sim particles not flat: {tps_not_flat.actual_sim_particles}")

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # physics
    sim.physics_manager.physics_list_name = "FTFP_INCLXX_EMZ"
    sim.physics_manager.set_production_cut("world", "all", 1000 * km)
    # sim.set_user_limits("phantom_a_2","max_step_size",1,['proton'])

    # create output dir, if it doesn't exist
    if not os.path.isdir(output_path):
        os.mkdir(output_path)

    # start simulation
    sim.run()
    output = sim.output

    # print results at the end
    stat = output.get_actor("Stats")
    print(stat)

    # ----------------------------------------------------------------------------------------------------------------
    # tests
    # with and without flat generation, the result in terms of dose should be identical
    d_names = ["edep_11", "edep_12", "edep_21", "edep_22"]
    dose_actors = [output.get_actor(d) for d in d_names]
    test = True

    # check that the dose output is the same
    print("--- Dose image spot 0 ---")
    test = (
        utility.assert_images(
            output_path / dose_actors[0].user_info.output,
            output_path / dose_actors[2].user_info.output,
            stat,
            tolerance=70,
            ignore_value=0,
        )
        and test
    )

    print("--- Dose image spot 1 ---")
    test = (
        utility.assert_images(
            output_path / dose_actors[1].user_info.output,
            output_path / dose_actors[3].user_info.output,
            stat,
            tolerance=70,
            ignore_value=0,
        )
        and test
    )

    # check that output with flat distribution has better statistics for the spot with less particles
    unc_vec = []
    for d, name in zip(dose_actors, d_names):
        edep_img = itk.imread(paths.output / d.user_info.output)
        edep_arr = itk.GetArrayViewFromImage(edep_img)
        unc_img = itk.imread(paths.output / d.user_info.output_uncertainty)
        unc_arr = itk.GetArrayFromImage(unc_img)
        # fig = utility.plot2D(unc_arr[0,:,:], d_actor, show=True)
        mean_unc = calculate_mean_unc(edep_arr, unc_arr, edep_thresh_rel=0.2)
        unc_vec.append(mean_unc)
        print(f"mean uncertainty {name}: {mean_unc}")

    test = unc_vec[1] < unc_vec[3] and test

    utility.test_ok(test)

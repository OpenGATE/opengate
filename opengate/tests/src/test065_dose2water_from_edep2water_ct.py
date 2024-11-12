#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
from opengate.tests import utility
from opengate.contrib.beamlines.ionbeamline import BeamlineModel
from opengate.contrib.tps.ionbeamtherapy import spots_info_from_txt

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test044_pbs", "test065_dose2water_from_edep2water_ct"
    )
    output_path = paths.output
    ref_path = paths.output_ref / ".." / "test059"

    # create output dir, if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 12365478910
    sim.random_engine = "MersenneTwister"
    sim.output_dir = output_path

    # units
    km = gate.g4_units.km
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    gcm3 = gate.g4_units.g_cm3

    # add a material database
    sim.volume_manager.add_material_database(paths.gate_data / "HFMaterials2014.db")

    ## Beamline model
    IR2HBL = BeamlineModel()
    IR2HBL.name = None
    IR2HBL.radiation_types = "ion 6 12"
    # Nozzle entrance to Isocenter distance
    IR2HBL.distance_nozzle_iso = 1300.00  # 1648 * mm#1300 * mm
    # SMX to Isocenter distance
    IR2HBL.distance_stearmag_to_isocenter_x = 6700.00
    # SMY to Isocenter distance
    IR2HBL.distance_stearmag_to_isocenter_y = 7420.00
    # polinomial coefficients
    IR2HBL.energy_mean_coeffs = [11.91893485094217, -9.539517997860457]
    IR2HBL.energy_spread_coeffs = [0.0004790681841295621, 5.253257865904452]
    IR2HBL.sigma_x_coeffs = [2.3335753978880014]
    IR2HBL.theta_x_coeffs = [0.0002944903217664001]
    IR2HBL.epsilon_x_coeffs = [0.0007872786903040108]
    IR2HBL.sigma_y_coeffs = [1.9643343053823967]
    IR2HBL.theta_y_coeffs = [0.0007911780133478402]
    IR2HBL.epsilon_y_coeffs = [0.0024916149017600447]

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]

    # source and beamline info
    beam_data_dict = spots_info_from_txt(
        ref_path / "TreatmentPlan4Gate-F5x5cm_E120MeVn.txt", "ion 6 12", beam_nr=1
    )
    gantry_angle = beam_data_dict["gantry_angle"]

    # nozzle box
    box = sim.add_volume("Box", "box")
    box.size = [500 * mm, 500 * mm, 1000 * mm]
    box.rotation = (
        Rotation.from_euler("z", gantry_angle, degrees=True)
        * Rotation.from_euler("x", -90, degrees=True)
    ).as_matrix()
    if gantry_angle == 0:
        box.translation = [0 * mm, -1148 * mm, 0 * mm]  # [1148 *mm, 0 * mm, 0 * mm]
    elif gantry_angle == 90:
        box.translation = [1148 * mm, 0 * mm, 0 * mm]
    box.material = "Vacuum"
    box.color = [0, 0, 1, 1]

    # nozzle WET
    nozzle = sim.add_volume("Box", "nozzle")
    nozzle.mother = box
    nozzle.size = [500 * mm, 500 * mm, 2 * mm]
    nozzle.material = "G4_WATER"

    # lookup tables
    hu_material = paths.data / "Schneider2000MaterialsTable.txt"
    hu_density = paths.data / "Schneider2000DensitiesTable.txt"

    # ct image
    mhd_ct_path = str(ref_path / "random_HU.mhd")

    # patient
    patient = sim.add_volume("Image", "patient")
    patient.image = mhd_ct_path
    # patient.mother = phantom.name
    # patient.translation = list((img_origin - origin_when_centered) - iso)
    patient.material = "G4_AIR"  # material used by default
    # patient.voxel_materials = [
    #     [-1024, -300, "G4_AIR"],
    #     [-300, 3000, "G4_WATER"],
    # ]
    sim.physics_manager.set_max_step_size(patient.name, 0.8)

    tol = 0.05 * gcm3
    (
        patient.voxel_materials,
        materials,
    ) = gate.geometry.materials.HounsfieldUnit_to_material(
        sim, tol, hu_material, hu_density
    )

    # physics
    sim.physics_manager.physics_list_name = "FTFP_INCLXX_EMZ"
    sim.physics_manager.set_production_cut("world", "all", 1000 * km)

    # add dose actor
    dose_postprocess = sim.add_actor("DoseActor", "dose_postprocess")
    dose_postprocess.dose.output_filename = "dose2water_ct_post.mhd"
    dose_postprocess.attached_to = patient
    dose_postprocess.size = [55, 63, 63]
    dose_postprocess.spacing = [1 * mm, 1 * mm, 1 * mm]
    dose_postprocess.hit_type = "random"
    dose_postprocess.dose.active = True
    dose_postprocess.score_in = "water"
    # OPTION CURRENTLY NOT AVAILABLE
    # dose_postprocess.dose_calc_on_the_fly = (
    #     False  # calc dose as edep/mass after end of simulation
    # )

    dose_in_step = sim.add_actor("DoseActor", "dose_in_step")
    dose_in_step.dose.output_filename = "dose2water_ct_step.mhd"
    dose_in_step.attached_to = patient
    dose_in_step.size = [55, 63, 63]
    dose_in_step.spacing = [1 * mm, 1 * mm, 1 * mm]
    dose_in_step.hit_type = "random"
    dose_in_step.dose.active = True
    dose_in_step.score_in = "water"
    # CURRENTLY DEACTIVATED OPTION
    # dose_in_step.dose_calc_on_the_fly = (
    #     False  # calculate dose directly in stepping action
    # )

    ## source
    nSim = 4000  # 328935  # particles to simulate per beam
    tps = sim.add_source("TreatmentPlanPBSource", "TP source")
    tps.beam_model = IR2HBL
    tps.n = nSim
    tps.beam_data_dict = beam_data_dict
    tps.beam_nr = 1
    tps.particle = "ion 6 12"

    # start simulation
    run_simulation = True
    if run_simulation:
        # add stat actor
        stat = sim.add_actor("SimulationStatisticsActor", "Stats")
        stat.track_types_flag = True
        # start simulation
        sim.run()

        # print results at the end
        print(stat)

    # read output
    d_post_path = dose_postprocess.dose.get_output_path()
    d_step_path = dose_in_step.dose.get_output_path()
    # img_mhd_out = itk.imread(d_post_path)
    # img_mhd_ref = itk.imread(d_step_path)

    ok = utility.assert_images(d_step_path, d_post_path, tolerance=10)

    utility.test_ok(ok)

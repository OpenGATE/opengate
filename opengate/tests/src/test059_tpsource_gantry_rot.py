#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import os
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
import opengate.element
from opengate.contrib.beamlines.ionbeamline import BeamlineModel
from opengate.contrib.tps.ionbeamtherapy import spots_info_from_txt, TreatmentPlanSource

if __name__ == "__main__":
    # ------ INITIALIZE SIMULATION ENVIRONMENT ----------
    paths = utility.get_default_test_paths(__file__, "gate_test044_pbs", "test059")
    output_path = paths.output
    ref_path = paths.output_ref

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
    s = gate.g4_units.s

    # add a material database
    sim.volume_manager.add_material_database(paths.gate_data / "HFMaterials2014.db")

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]

    ## ---------- DEFINE BEAMLINE MODEL -------------##
    beamline = BeamlineModel()
    beamline.name = None
    beamline.radiation_types = "ion 6 12"
    # Nozzle entrance to Isocenter distance
    beamline.distance_nozzle_iso = 1300.00  # 1648 * mm#1300 * mm
    # SMX to Isocenter distance
    beamline.distance_stearmag_to_isocenter_x = 6700.00
    # SMY to Isocenter distance
    beamline.distance_stearmag_to_isocenter_y = 7420.00
    # polinomial coefficients
    beamline.energy_mean_coeffs = [11.91893485094217, -9.539517997860457]
    beamline.energy_spread_coeffs = [0.0004790681841295621, 5.253257865904452]
    beamline.sigma_x_coeffs = [2.3335753978880014]
    beamline.theta_x_coeffs = [0.0002944903217664001]
    beamline.epsilon_x_coeffs = [0.0007872786903040108]
    beamline.sigma_y_coeffs = [1.9643343053823967]
    beamline.theta_y_coeffs = [0.0007911780133478402]
    beamline.epsilon_y_coeffs = [0.0024916149017600447]

    # NOTE: HBL means that the beam is coming from -x (90 degree rot around y)
    nSim = 20000  # particles to simulate per beam
    # rt_plan = ref_path / "RP1.2.752.243.1.1.20220406175810679.4500.52008_tagman.dcm"
    # beamset = BeamsetInfo(rt_plan)
    # G = float(beamset.beam_angles[0])

    ## ----  VBL Nozzle  ---
    # nozzle box
    box = sim.add_volume("Box", "box")
    box.size = [500 * mm, 500 * mm, 1000 * mm]
    box.rotation = Rotation.from_euler("x", -90, degrees=True).as_matrix()
    box.translation = [0.0, -1148 * mm, 0.0]
    box.material = "Vacuum"
    box.color = [0, 0, 1, 1]

    # nozzle WET
    nozzle = sim.add_volume("Box", "nozzle")
    nozzle.mother = box.name
    nozzle.size = [500 * mm, 500 * mm, 2 * mm]
    nozzle.material = "G4_WATER"

    # Rashi
    rashi = sim.add_volume("Box", "rashi")
    rashi.mother = box.name
    rashi.size = [500 * mm, 500 * mm, 5 * mm]
    rashi.translation = [0.0, 0.0, 200 * mm]
    rashi.material = "G4_LUCITE"
    rashi.color = [1, 0, 1, 1]

    ## ----  HBL Nozzle  ---
    # FIXME : will change after volumes are refactored
    box_rot = sim.add_volume("Box", "box_rot")
    box_rot.copy_user_info(box)
    box_rot.rotation = Rotation.from_euler("y", -90, degrees=True).as_matrix()
    box_rot.translation = [1148.0, 0.0, 1000.0]

    nozzle_rot = sim.add_volume("Box", "nozzle_rot")
    nozzle_rot.copy_user_info(nozzle)
    nozzle_rot.mother = box_rot.name

    rashi_rot = sim.add_volume("Box", "rashi_rot")
    rashi_rot.copy_user_info(rashi)
    rashi_rot.mother = box_rot.name

    # -----------------------------------

    # target 1 VBL
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [324 * mm, 324 * mm, 324 * mm]
    phantom.translation = [0 * mm, 0.0, 0.0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    # target 2 HBL
    phantom_rot = sim.add_volume("Box", "phantom_rot")
    phantom_rot.copy_user_info(phantom)
    phantom_rot.rotation = Rotation.from_euler("z", 90, degrees=True).as_matrix()
    phantom_rot.translation = [0.0, 0.0, 1000.0]

    # add dose actor
    dose = sim.add_actor("DoseActor", "doseInXYZ")
    dose.output_filename = "testTPSgantry.mhd"
    dose.attached_to = phantom.name
    dose.size = [162, 1620, 162]
    dose.spacing = [2.0, 0.2, 2.0]
    dose.hit_type = "random"
    dose.user_output.dose.active = True

    dose_rot = sim.add_actor("DoseActor", "doseInXYZ_rot")
    dose_rot.copy_user_info(dose)
    dose_rot.attached_to = phantom_rot.name
    dose_rot.output_filename = "testTPSganry_rot.mhd"

    # physics
    sim.physics_manager.physics_list_name = "FTFP_INCLXX_EMZ"
    sim.physics_manager.set_production_cut("world", "all", 1000 * km)

    # add TPSources
    beam_data_dict = spots_info_from_txt(
        ref_path / "TreatmentPlan4Gate-1D_HBL_120.txt", "ion 6 12", beam_nr=1
    )

    tps_rot = sim.add_source("TreatmentPlanPBSource", "HBL")
    tps_rot.n = nSim
    tps_rot.end_time = 0.5 * s
    tps_rot.beam_model = beamline
    tps_rot.beam_data_dict = beam_data_dict
    tps_rot.beam_nr = 1
    tps_rot.particle = "ion 6 12"
    tps_rot.position.translation = [0.0, 0.0, 1000.0]
    tps_rot.sorted_spot_generation = True

    beam_data_dict_vbl = beam_data_dict.copy()
    beam_data_dict_vbl["gantry_angle"] = 0

    tps = sim.add_source("TreatmentPlanPBSource", "VBL")
    tps.n = nSim
    tps.start_time = 0.5 * s
    tps.beam_model = beamline
    tps.beam_data_dict = beam_data_dict_vbl
    tps.beam_nr = 1
    tps.particle = "ion 6 12"
    tps.sorted_spot_generation = True

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # create output dir, if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # start simulation
    sim.run()

    # print results at the end
    print(stats)

    ## ------ TESTS -------##

    # ABSOLUTE DOSE
    # ok = utility.assert_images(
    #     dose.output,
    #     dose_rot.output,
    #     stat,
    #     tolerance=50,
    #     ignore_value=0,
    # )
    ok = True

    # read output and ref
    img_mhd_out = itk.imread(
        output_path / sim.get_actor("doseInXYZ_rot").get_output_path("edep")
    )
    img_mhd_ref = itk.imread(
        output_path / sim.get_actor("doseInXYZ").get_output_path("edep")
    )
    data = itk.GetArrayViewFromImage(img_mhd_out)
    data_ref = itk.GetArrayViewFromImage(img_mhd_ref)
    spacing = img_mhd_out.GetSpacing()

    # Range 80
    ok = (
        utility.compareRange(
            data, data_ref, data.shape, data_ref.shape, spacing, spacing
        )
        and ok
    )

    # 1D plots
    # fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    # gate.plot_img_axis(ax, img_mhd_out, "y profile", axis="y")
    # gate.plot_img_axis(ax, img_mhd_ref, "y ref", axis="y")
    # fig.savefig(output_path / "dose_profiles_water.png")
    # plt.show()

    utility.test_ok(ok)

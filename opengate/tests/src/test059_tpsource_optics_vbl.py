#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
from opengate.contrib.beamlines.ionbeamline import BeamlineModel
from opengate.contrib.tps.ionbeamtherapy import spots_info_from_txt, TreatmentPlanSource

if __name__ == "__main__":
    # ------ INITIALIZE SIMULATION ENVIRONMENT ----------
    paths = utility.get_default_test_paths(
        __file__, "gate_test044_pbs", output_folder="test059"
    )
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
    um = gate.g4_units.um
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm
    deg = gate.g4_units.deg
    rad = gate.g4_units.rad

    # add a material database
    sim.volume_manager.add_material_database(paths.gate_data / "HFMaterials2014.db")

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]

    # nozzle box
    box = sim.add_volume("Box", "box")
    box.size = [500 * mm, 500 * mm, 1000 * mm]
    box.rotation = Rotation.from_euler("x", -90, degrees=True).as_matrix()
    box.translation = [0.0, -1148 * mm, 0.0]
    box.material = "Air"
    box.color = [0, 0, 1, 1]

    # nozzle WET
    nozzle = sim.add_volume("Box", "nozzle")
    nozzle.mother = box.name
    nozzle.size = [500 * mm, 500 * mm, 2 * mm]
    nozzle.material = "G4_WATER"

    # target
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [300 * mm, 310 * mm, 310 * mm]
    phantom.rotation = Rotation.from_euler("z", -90, degrees=True).as_matrix()
    phantom.translation = [0.0, -150 * mm, 0.0]
    phantom.material = "G4_AIR"
    phantom.color = [0, 0, 1, 1]
    sim.physics_manager.set_max_step_size(phantom.name, 0.8)

    # physics
    sim.physics_manager.physics_list_name = "FTFP_INCLXX_EMZ"
    sim.physics_manager.set_production_cut("world", "all", 1000 * km)

    # add dose actor
    dose = sim.add_actor("DoseActor", "doseInXYZ")
    dose.output_filename = "TPS_optics_vbl.mhd"
    dose.attached_to = phantom.name
    dose.size = [30, 620, 620]
    dose.spacing = [10.0, 0.5, 0.5]
    dose.hit_type = "random"
    dose.dose.active = True

    # ---------- DEFINE BEAMLINE MODEL -------------
    IR2VBL = BeamlineModel()
    IR2VBL.name = None
    IR2VBL.radiation_types = "ion 6 12"
    # Nozzle entrance to Isocenter distance
    IR2VBL.distance_nozzle_iso = 1300.00  # 1648 * mm#1300 * mm
    # SMX to Isocenter distance
    IR2VBL.distance_stearmag_to_isocenter_x = 6700.00
    # SMY to Isocenter distance
    IR2VBL.distance_stearmag_to_isocenter_y = 7420.00
    # polinomial coefficients
    IR2VBL.energy_mean_coeffs = [11.91893485094217, -9.539517997860457]
    IR2VBL.energy_spread_coeffs = [0.0004790681841295621, 5.253257865904452]
    IR2VBL.sigma_x_coeffs = [-0.00011142901344618727, 2.346946879501544]
    IR2VBL.theta_x_coeffs = [-3.6368814874049214e-07, 0.0003381328996152591]
    IR2VBL.epsilon_x_coeffs = [3.1292233857396716e-06, 0.0004117718840152502]
    IR2VBL.sigma_y_coeffs = [-0.0004009682717802152, 2.0124504979960225]
    IR2VBL.theta_y_coeffs = [-8.437400716390318e-07, 0.000892426821944524]
    IR2VBL.epsilon_y_coeffs = [-8.757558864087579e-08, 0.00250212397239695]

    # --------START PENCIL BEAM SCANNING----------
    # nSim = 328935  # particles to simulate per beam
    nSim = 20000
    tps = sim.add_source("TreatmentPlanPBSource", "TP source")
    tps.beam_model = IR2VBL
    tps.n = nSim
    tps.particle = "ion 6 12"
    tps.plan_path = ref_path / "TreatmentPlan4Gate-gate_test59tps_v.txt"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # create output dir, if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # start simulation
    sim.run()

    # -------------END SCANNING-------------
    # print results at the end
    print(stats)

    # ------ TESTS -------
    # dose_path = utility.scale_dose(
    #     str(dose.output).replace(".mhd", "_dose.mhd"),
    #     ntot / actual_sim_particles,
    # )

    # SPOT POSITIONS COMPARISON
    # read output and ref
    img_mhd_out = itk.imread(dose.get_output_path("dose"))
    img_mhd_ref = itk.imread(
        ref_path / "idc-PHANTOM-air_box_vbl-gate_test59tps_v-PLAN-Physical.mhd"
    )
    data = itk.GetArrayViewFromImage(img_mhd_out)
    data_ref = itk.GetArrayViewFromImage(img_mhd_ref)
    shape = data.shape
    spacing = img_mhd_out.GetSpacing()

    # spot comparison (N.B x and z are inverted in np array!)
    # spots in the plan file
    yz = [
        0,
        50,
        0,
        0,
        -62.507,
        -21.669,
        -61.951,
        -72.23,
        50,
        -50,
        50,
        0,
        50,
        50,
        -50,
        50,
    ]

    yzM = np.array(yz).reshape(int(len(yz) / 2), 2)
    # convert from mm (wrt image center) to voxel
    spot_y = [int(y / dose.spacing[1]) + int(dose.size[1] / 2) for y in yzM[:, 0]]
    spot_z = [int(z / dose.spacing[1]) + int(dose.size[1] / 2) for z in yzM[:, 1]]

    thresh = 0.105

    # 1D
    fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    utility.plot_img_axis(ax, img_mhd_out, "z profile", axis="z")
    utility.plot_img_axis(ax, img_mhd_out, "x profile", axis="x")
    utility.plot_img_axis(ax, img_mhd_out, "y profile", axis="y")

    # fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    utility.plot_img_axis(ax, img_mhd_ref, "z ref", axis="z")
    utility.plot_img_axis(ax, img_mhd_ref, "x ref", axis="x")
    utility.plot_img_axis(ax, img_mhd_ref, "y ref", axis="y")
    fig.savefig(output_path / "dose_profiles_spots_vbl.png")

    ok = True
    for i in range(1, shape[2], shape[2] // 3):
        # check i-th slab
        print(f"Airslab nr. {i}")
        # gate.plot2D(data[:, :, i], "2D Edep opengate", show=True)
        # gate.plot2D(data_ref[:, :, i], "2D Edep gate", show=True)
        for y, z in zip(spot_y, spot_z):
            # i = 0
            print(f" ({y:.2f},{z:.2f})")
            # 'cut' the slab around the spot expected in y,z
            w = 30  # cut window's half size
            d_out = data[z - w : z + w, y - w : y + w, i : i + 1]
            d_ref = data_ref[z - w : z + w, y - w : y + w, i : i + 1]
            ok = (
                utility.test_tps_spot_size_positions(
                    d_out, d_ref, spacing, thresh=thresh, abs_tol=0.3
                )
                and ok
            )

    utility.test_ok(ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import os
import numpy as np
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
from opengate.contrib.beamlines.ionbeamline import BeamlineModel
from opengate.contrib.tps.ionbeamtherapy import spots_info_from_txt, TreatmentPlanSource

if __name__ == "__main__":
    # ------ INITIALIZE SIMULATION ENVIRONMENT ----------
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
    ui.random_seed = 12365478910
    ui.random_engine = "MersenneTwister"

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
    sim.add_material_database(paths.gate_data / "HFMaterials2014.db")

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]

    # nozzle box
    box = sim.add_volume("Box", "box")
    box.size = [500 * mm, 500 * mm, 1000 * mm]
    box.translation = [1148 * mm, 0.0, 0.0]
    box.rotation = Rotation.from_euler("y", -90, degrees=True).as_matrix()
    box.material = "Vacuum"
    box.color = [0, 0, 1, 1]

    # nozzle WET
    nozzle = sim.add_volume("Box", "nozzle")
    nozzle.mother = box.name
    nozzle.size = [500 * mm, 500 * mm, 2 * mm]
    nozzle.material = "G4_WATER"

    # target
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [500 * mm, 500 * mm, 400 * mm]
    phantom.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    phantom.translation = [-200.0, 0.0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    # roos chamber
    roos = sim.add_volume("Tubs", "roos")
    roos.mother = phantom.name
    roos.material = "G4_WATER"
    roos.rmax = 7.8
    roos.rmin = 0
    roos.dz = 200
    roos.color = [1, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = (
        "FTFP_INCLXX_EMZ"  # 'QGSP_BIC_HP_EMZ' #"FTFP_INCLXX_EMZ"
    )

    sim.physics_manager.set_production_cut("world", "all", 1000 * km)

    # add dose actor
    dose = sim.add_actor("DoseActor", "doseInXYZ")
    dose.output = output_path / "abs_dose_roos.mhd"
    dose.mother = roos.name
    dose.size = [1, 1, 800]
    dose.spacing = [15.6, 15.6, 0.5]
    dose.hit_type = "random"
    dose.gray = True

    ## ---------- DEFINE BEAMLINE MODEL -------------##
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

    ## --------START PENCIL BEAM SCANNING---------- ##
    # NOTE: HBL means that the beam is coming from -x (90 degree rot around y)

    nSim = 50000  # 328935  # particles to simulate per beam

    spots, ntot, energies, G = spots_info_from_txt(
        ref_path / "TreatmentPlan4Gate-F5x5cm_E120MeVn.txt", "ion 6 12"
    )
    tps = TreatmentPlanSource("RT_plan", sim)
    tps.set_beamline_model(IR2HBL)
    tps.set_particles_to_simulate(nSim)
    tps.set_spots(spots)
    tps.rotation = Rotation.from_euler("z", G, degrees=True)
    tps.initialize_tpsource()

    actual_sim_particles = tps.actual_sim_particles

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    # start simulation

    # create output dir, if it doesn't exist
    if not os.path.isdir(output_path):
        os.mkdir(output_path)

    sim.run()
    output = sim.output

    ## -------------END SCANNING------------- ##
    # print results at the end
    stat = output.get_actor("Stats")
    print(stat)

    ## ------ TESTS -------##
    dose_path = utility.scale_dose(
        str(dose.output).replace(".mhd", "_dose.mhd"),
        ntot / actual_sim_particles,
        output_path / "threeDdoseWaternew.mhd",
    )

    # ABSOLUTE DOSE

    # read output and ref
    img_mhd_out = itk.imread(dose_path)
    img_mhd_ref = itk.imread(
        ref_path / "idc-PHANTOM-roos-F5x5cm_E120MeVn-PLAN-Physical.mhd"
    )
    data = itk.GetArrayViewFromImage(img_mhd_out)
    data_ref = itk.GetArrayViewFromImage(img_mhd_ref)
    shape = data.shape
    spacing = img_mhd_out.GetSpacing()
    spacing_ref = np.flip(img_mhd_ref.GetSpacing())

    ok = utility.assert_img_sum(
        img_mhd_out,
        img_mhd_ref,
    )

    points = 400 - np.linspace(10, 14, 9)
    ok = (
        utility.compare_dose_at_points(
            points,
            data,
            data_ref,
            shape,
            data_ref.shape,
            spacing,
            spacing_ref,
            axis1="z",
            axis2="x",
            rel_tol=0.03,
        )
        and ok
    )

    # 1D
    # fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    # gate.plot_img_axis(ax, img_mhd_out, "x profile", axis="z")
    # gate.plot_img_axis(ax, img_mhd_ref, "x ref", axis="z")
    # plt.show()

    # fig.savefig(output_path / "dose_profiles_water.png")

    utility.test_ok(ok)

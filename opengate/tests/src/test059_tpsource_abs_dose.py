#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import numpy as np
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
from opengate.contrib.beamlines.ionbeamline import BeamlineModel
from opengate.contrib.tps.ionbeamtherapy import spots_info_from_txt
import matplotlib.pyplot as plt
from opengate.tests.utility import plot_img_axis

if __name__ == "__main__":
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
    sim.world.size = [600 * cm, 500 * cm, 500 * cm]

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
    dose.output_filename = "abs_dose_roos.mhd"
    dose.attached_to = roos.name
    dose.size = [1, 1, 800]
    dose.spacing = [15.6, 15.6, 0.5]
    dose.hit_type = "random"
    dose.dose.active = True

    # ---------- DEFINE BEAMLINE MODEL -------------#
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

    # --------START PENCIL BEAM SCANNING---------- #
    # NOTE: HBL means that the beam is coming from -x (90 degree rot around y)
    nSim = 50000  # 328935  # particles to simulate per beam
    beam_data_dict = spots_info_from_txt(
        ref_path / "TreatmentPlan4Gate-F5x5cm_E120MeVn.txt", "ion 6 12", beam_nr=1
    )
    tps = sim.add_source("TreatmentPlanPBSource", "TPSource")
    tps.n = nSim
    tps.sorted_spot_generation = True
    tps.beam_model = IR2HBL
    tps.beam_data_dict = beam_data_dict
    tps.beam_nr = 1
    tps.particle = "ion 6 12"
    ntot = beam_data_dict["msw_beam"]

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    # create output dir, if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # start simulation
    sim.run()

    # -------------END SCANNING------------- #
    # print results at the end
    print(stats)

    # ------ TESTS -------#
    dose_path = utility.scale_dose(
        str(dose.get_output_path("dose")),
        ntot / nSim,
        output_path / "abs_dose_roos-Scaled.mhd",
    )

    # ABSOLUTE DOSE

    # read output and ref
    f = ref_path / "idc-PHANTOM-roos-F5x5cm_E120MeVn-PLAN-Physical.mhd"
    print("Compare", dose_path, f)
    img_mhd_out = itk.imread(dose_path)
    img_mhd_ref = itk.imread(f)
    data = itk.GetArrayViewFromImage(img_mhd_out)
    data_ref = itk.GetArrayViewFromImage(img_mhd_ref)
    shape = data.shape
    spacing = img_mhd_out.GetSpacing()
    spacing_ref = np.flip(img_mhd_ref.GetSpacing())

    ok = utility.assert_img_sum(img_mhd_out, img_mhd_ref, sum_tolerance=5.5)

    print("compare dose at points")
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
            rel_tol=0.065,
        )
        and ok
    )

    # 1D
    """fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    plot_img_axis(ax, img_mhd_out, "x profile", axis="z")
    plot_img_axis(ax, img_mhd_ref, "x ref", axis="z")
    plt.show()
    fig.savefig(output_path / "dose_profiles_water.png")"""

    utility.test_ok(ok)

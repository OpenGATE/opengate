#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
from opengate.contrib.beamlines.ionbeamline import BeamlineModel
import numpy as np

from opengate.tests.utility import print_test

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
    peak_finder = sim.add_volume("Tubs", "peak_finder")
    peak_finder.mother = phantom.name
    peak_finder.material = "G4_WATER"
    peak_finder.rmax = 40.3
    peak_finder.rmin = 0
    peak_finder.dz = 200
    peak_finder.color = [1, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "FTFP_INCLXX_EMZ"
    sim.physics_manager.set_production_cut("world", "all", 1000 * km)

    # add dose actor
    dose_actor = sim.add_actor("DoseActor", "doseInXYZ")
    dose_actor.output_filename = "dose_peak_finder.mhd"
    dose_actor.attached_to = peak_finder.name
    dose_actor.size = [1, 1, 8000]
    dose_actor.spacing = [80.6, 80.6, 0.05]
    dose_actor.hit_type = "random"
    dose_actor.dose.active = True

    # ---------- DEFINE BEAMLINE MODEL -------------
    IR2HBL = BeamlineModel()
    IR2HBL.name = None
    IR2HBL.radiation_types = "ion 6 12"
    # Nozzle entrance to Isocenter distance
    IR2HBL.distance_nozzle_iso = 1300.00  # 1648 * mm#1300 * mm
    # SMX to Isocenter distance
    IR2HBL.distance_stearmag_to_isocenter_x = 2000.00
    # SMY to Isocenter distance
    IR2HBL.distance_stearmag_to_isocenter_y = 2000.00
    # polinomial coefficients
    IR2HBL.energy_mean_coeffs = [12.0, -9.54]
    IR2HBL.energy_spread_coeffs = [0.00048, 5.2532]
    IR2HBL.sigma_x_coeffs = [2.33]
    IR2HBL.theta_x_coeffs = [0.00029]
    IR2HBL.epsilon_x_coeffs = [0.00078]
    IR2HBL.sigma_y_coeffs = [1.96]
    IR2HBL.theta_y_coeffs = [0.00079]
    IR2HBL.epsilon_y_coeffs = [0.0024]

    # --------START PENCIL BEAM SCANNING----------
    # NOTE: HBL means that the beam is coming from -x (90 degree rot around y)

    tps = sim.add_source("TreatmentPlanPBSource", "TPSource")
    tps.n = 20000
    tps.beam_model = IR2HBL
    tps.plan_path = ref_path / "PlanCentralSpot_1440MeV.txt"
    tps.beam_nr = 1
    tps.particle = "ion 6 12"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    # s.track_types_flag = True

    # start simulation
    sim.run()

    # -------------END SCANNING-------------
    # print results at the end
    print(stats)

    # ------ TESTS -------##
    dose_path = output_path / sim.get_actor("doseInXYZ").dose.get_output_path()

    # RANGE

    # read output and ref
    print("Compare ", dose_path)
    img_mhd_out = itk.imread(dose_path)
    # data = np.flip(itk.GetArrayViewFromImage(img_mhd_out), axis=0)
    data = itk.GetArrayViewFromImage(img_mhd_out)
    spacing = np.array(img_mhd_out.GetSpacing())
    print(data.shape, spacing)

    # Range 80
    range80_gate9_E120MeV = 367.06
    range_opengate = utility.get_range_from_image(data, data.shape, spacing, axis="z")

    thresh = 2.0 * mm
    ok = True
    print(f"range_opengate = {range_opengate}")
    print(f"range80_gate9_E120MeV = {range80_gate9_E120MeV}")
    if abs(range_opengate - range80_gate9_E120MeV) > thresh:
        ok = False
    print_test(
        ok, f"Compare ranges {range_opengate} and {range80_gate9_E120MeV} >? {thresh}"
    )

    utility.test_ok(ok)

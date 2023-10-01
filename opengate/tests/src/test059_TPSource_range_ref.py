#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import os
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
from opengate.contrib.beamlines.ionbeamline import BeamlineModel
from opengate.contrib.tps.ionbeamtherapy import TreatmentPlanSource, spots_info_from_txt

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
    peak_finder = sim.add_volume("Tubs", "peak_finder")
    peak_finder.mother = phantom.name
    peak_finder.material = "G4_WATER"
    peak_finder.rmax = 40.3
    peak_finder.rmin = 0
    peak_finder.dz = 200
    peak_finder.color = [1, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = (
        "FTFP_INCLXX_EMZ"  # 'QGSP_BIC_HP_EMZ' #"FTFP_INCLXX_EMZ"
    )
    sim.physics_manager.set_production_cut("world", "all", 1000 * km)

    # add dose actor
    dose = sim.add_actor("DoseActor", "doseInXYZ")
    dose.output = output_path / "dose_peak_finder.mhd"
    dose.mother = peak_finder.name
    dose.size = [1, 1, 8000]
    dose.spacing = [80.6, 80.6, 0.05]
    dose.hit_type = "random"
    dose.gray = True

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
    nSim = 20000  # 328935  # particles to simulate per beam
    spots, ntot, energies, G = spots_info_from_txt(
        ref_path / "PlanCentralSpot_1440MeV.txt", "ion 6 12"
    )
    tps = TreatmentPlanSource("RT_plan", sim)
    tps.set_beamline_model(IR2HBL)
    tps.set_particles_to_simulate(nSim)
    tps.set_spots(spots)
    tps.rotation = Rotation.from_euler("z", G, degrees=True)
    tps.initialize_tpsource()

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # create output dir, if it doesn't exist
    if not os.path.isdir(output_path):
        os.mkdir(output_path)

    # start simulation
    sim.run()
    output = sim.output

    # -------------END SCANNING-------------
    # print results at the end
    stat = output.get_actor("Stats")
    print(stat)

    # ------ TESTS -------
    dose_path = str(dose.output).replace(".mhd", "_dose.mhd")

    # RANGE

    # read output and ref
    img_mhd_out = itk.imread(dose_path)
    data = itk.GetArrayViewFromImage(img_mhd_out)
    shape = data.shape
    spacing = img_mhd_out.GetSpacing()

    # Range 80
    range80_gate9_E120MeV = 367.06
    range_opengate = utility.get_range_from_image(data, data.shape, spacing, axis="z")

    thresh = 2.0 * mm
    ok = True
    if abs(range_opengate - range80_gate9_E120MeV) > thresh:
        ok = False

    utility.test_ok(ok)

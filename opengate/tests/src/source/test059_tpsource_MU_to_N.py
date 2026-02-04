#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import numpy as np
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
from opengate.contrib.beamlines.ionbeamline import BeamlineModel
from opengate.contrib.tps.ionbeamtherapy import SpotInfo

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
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    #  change world size
    sim.world.size = [600 * cm, 500 * cm, 500 * cm]

    # physics
    sim.physics_manager.physics_list_name = (
        "FTFP_INCLXX_EMZ"  # 'QGSP_BIC_HP_EMZ' #"FTFP_INCLXX_EMZ"
    )

    sim.physics_manager.set_production_cut("world", "all", 1000 * km)

    # beamline model
    beamline = BeamlineModel()
    beamline.name = None
    beamline.radiation_types = "proton"
    beamline.distance_nozzle_iso = (
        250 * mm
    )  # distance from nozzle to isocenter, starts at the edge of the world

    # polinomial coefficients
    beamline.energy_mean_coeffs = [1, 0]  #
    beamline.energy_spread_coeffs = [0.01]  # [0.4417036946562556]
    beamline.sigma_x_coeffs = [0.00016686, -0.076132159, 11.88305136]
    beamline.theta_x_coeffs = [-2.6000e-06, 0.00050119, -0.018560476]
    beamline.epsilon_x_coeffs = [0.0241]
    beamline.sigma_y_coeffs = [0.00016686, -0.076132159, 11.88305136]
    beamline.theta_y_coeffs = [-2.6000e-06, 0.00050119, -0.018560476]
    beamline.epsilon_y_coeffs = [0.0241]
    beamline.MU_to_N_coeffs = [1e-4, 0, 0]  # quadratic dependency

    # create fake plan, with spot weight in MU.
    # MU per spot:
    #   Spot1: 1e3
    #   Spot2: 3e3
    # MU to N factors:
    #   E 100 MeV -> 1.0
    #   E 200 Mev -> 4.0
    # N primaries from MU
    #   Spot1: 1.0*1e3 = 1e3
    #   Spot2: 4.0*3e3 = 12e3
    # PDF in n primaries: [1/13, 12/13]
    # we want to verify that the pdf is calculated correctly by the TP source
    beam_data = dict()
    spot1 = SpotInfo(-1, 0, 1e3, 100)
    spot1.beamFraction = 1 / 4
    spot2 = SpotInfo(1, 0, 3e4, 200)
    spot2.beamFraction = 3 / 4
    beam_data["n_fields"] = 1
    beam_data["plan_name"] = ""
    beam_data["msw_beam"] = 4e4
    beam_data["energies"] = [100, 200]
    beam_data["nb_spots"] = [1, 1]
    beam_data["spots"] = [spot1, spot2]
    beam_data["gantry_angle"] = 0
    beam_data["couch_angle"] = 0
    beam_data["isocenter"] = []

    tps = sim.add_source("TreatmentPlanPBSource", "TPSource")
    tps.n = 2000
    tps.sorted_spot_generation = True
    tps.beam_model = beamline
    tps.beam_data_dict = beam_data
    tps.beam_nr = 1
    tps.particle = "proton"
    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    # create output dir, if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # start simulation
    sim.run()
    print(stats)

    # ------ TEST -------#
    print(tps.pdf)
    expected_pdf = [1 / 13, 12 / 13]
    actual_pdf = tps.pdf
    utility.test_ok(expected_pdf == actual_pdf)

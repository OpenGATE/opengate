#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import os
from opengate.tests import utility
import opengate as gate
from opengate.contrib.beamlines.ionbeamline import BeamlineModel
from opengate.contrib.tps.ionbeamtherapy import spots_info_from_txt, TreatmentPlanSource

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

    # FIRST DETECTOR
    # box
    # translation and rotation like in the Gate macro
    box1 = sim.add_volume("Box", "box1")
    box1.size = [10 * cm, 10 * cm, 105 * cm]
    box1.translation = [0 * cm, 0 * cm, 52.5 * cm]
    box1.material = "Vacuum"
    box1.color = [0, 0, 1, 1]

    # phantoms
    m = Rotation.identity().as_matrix()

    phantom = sim.add_volume("Box", "phantom_a_1")
    phantom.mother = "box1"
    phantom.size = [100 * mm, 100 * mm, 50 * mm]
    phantom.translation = [0 * mm, 0 * mm, -500 * mm]
    phantom.rotation = m
    phantom.material = "G4_AIR"
    phantom.color = [1, 0, 1, 1]

    # add dose actor
    dose = sim.add_actor("DoseActor", "doseInYZ_1")
    filename = "phantom_a_1.mhd"
    dose.output = output_path / filename
    dose.mother = "phantom_a_1"
    dose.size = [250, 250, 1]
    dose.spacing = [0.4, 0.4, 2]
    dose.hit_type = "random"

    # SECOND DETECTOR
    # box
    # translation and rotation like in the Gate macro
    box2 = sim.add_volume("Box", "box2")
    box2.size = [10 * cm, 10 * cm, 105 * cm]
    box2.translation = [30 * cm, 0 * cm, 52.5 * cm]
    box2.material = "Vacuum"
    box2.color = [0, 0, 1, 1]

    # phantoms
    m = Rotation.identity().as_matrix()

    phantom2 = sim.add_volume("Box", "phantom_a_2")
    phantom2.mother = "box2"
    phantom2.size = [100 * mm, 100 * mm, 50 * mm]
    phantom2.translation = [0 * mm, 0 * mm, -500 * mm]
    phantom2.rotation = m
    phantom2.material = "G4_AIR"
    phantom2.color = [1, 0, 1, 1]

    # add dose actor
    dose2 = sim.add_actor("DoseActor", "doseInYZ_2")
    filename = "phantom_a_2.mhd"
    dose2.output = output_path / filename
    dose2.mother = "phantom_a_2"
    dose2.size = [250, 250, 1]
    dose2.spacing = [0.4, 0.4, 2]
    dose2.hit_type = "random"

    # TPS SOURCE
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
    nSim = 60000  # particles to simulate per beam
    spots, ntot, energies, G = spots_info_from_txt(
        ref_path / "TreatmentPlan2Spots.txt", "proton"
    )
    tps = TreatmentPlanSource("test", sim)
    tps.set_beamline_model(beamline)
    tps.set_particles_to_simulate(nSim)
    tps.set_spots(spots)
    tps.rotation = Rotation.from_euler("x", 90, degrees=True)
    tps.initialize_tpsource()

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

    # energy deposition: we expect the edep from source two
    # to be double the one of source one

    print("Compare tps Edep to single pb sources")
    print(" --------------------------------------- ")
    mhd_1 = "phantom_a_1.mhd"
    mhd_2 = "phantom_a_2.mhd"
    test = True

    # check first spot
    test = (
        utility.assert_images(
            ref_path / mhd_1,
            output_path / mhd_1,
            stat,
            tolerance=70,
            ignore_value=0,
        )
        and test
    )

    # check second spot
    test = (
        utility.assert_images(
            ref_path / mhd_1,
            output_path / mhd_1,
            stat,
            tolerance=70,
            ignore_value=0,
        )
        and test
    )
    print(" --------------------------------------- ")
    # fig1 = utility.create_2D_Edep_colorMap(output_path / mhd_1, show=True)
    # fig2 = utility.create_2D_Edep_colorMap(output_path / mhd_2, show=True)

    print("Compare ratio of the two spots with expected ratio")

    # Total Edep
    is_ok = (
        utility.test_weights(
            2,
            output_path / mhd_1,
            output_path / mhd_2,
            thresh=0.2,
        )
        and test
    )

    utility.test_ok(is_ok)

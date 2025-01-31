#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
import matplotlib.pyplot as plt

if __name__ == "__main__":
    do_debug = False
    output_path = "/home/fava/04_Calculations/rbe_carbon_output"
    # paths = utility.get_default_test_paths(
    #     __file__, "test050_let_actor_letd", "test050"
    # )
    # ref_path = paths.output_ref

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 1234567891
    sim.number_of_threads = 1
    sim.output_dir = output_path  # paths.output

    numPartSimTest = 1e3 / sim.number_of_threads
    numPartSimRef = 1e5

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    mrad = gate.g4_units.mrad
    km = gate.g4_units.km
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]
    # world.material = "Vacuum"

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 10 * cm]
    phantom.translation = [-5 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    test_material_name = "G4_WATER"
    phantom_off = sim.add_volume("Image", "phantom_off")
    phantom_off.image = "/var/work/IDEAL-1_2ref/fava_1D_IDEAL_HBL_ISD50_RS_163__1_2024_10_07_14_22_20/rungate.0/ct_orig.mhd"
    phantom_off.mother = phantom.name
    # phantom_off.size = [100 * mm, 60 * mm, 60 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    # phantom_off.material = test_material_name
    phantom_off.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "Shielding_EMZ"
    # sim.physics_manager.set_production_cut("world", "all", 1000 * km)
    # FIXME need SetMaxStepSizeInRegion ActivateStepLimiter
    # now available
    # e.g.
    # sim.physics_manager.set_max_step_size(volume_name='phantom', max_step_size=1*mm)

    # default source for tests
    source = sim.add_source("IonPencilBeamSource", "mysource1")
    source.energy.type = "gauss"
    source.energy.mono = 4833.6 * MeV
    source.particle = "ion 6 12"
    source.position.type = "disc"
    # rotate the disc, equiv to : rot1 0 1 0 and rot2 0 0 1
    source.direction.type = "momentum"
    source.position.rotation = Rotation.from_euler("y", -90, degrees=True).as_matrix()
    source.n = numPartSimTest
    # source.position.sigma_x = 8 * mm
    # source.position.sigma_y = 8 * mm
    source.direction.partPhSp_x = [
        2.3335754 * mm,
        2.3335754 * mrad,
        0.00078728 * mm * mrad,
        0,
    ]
    source.direction.partPhSp_y = [
        1.96433431 * mm,
        0.00079118 * mrad,
        0.00249161 * mm * mrad,
        0,
    ]

    size = [50, 6, 6]
    spacing = [2.0 * mm, 10.0 * mm, 10.0 * mm]

    RBEActorName_IDD_d = "RBEActorOG_d"
    RBEActor_IDD_d = sim.add_actor("RBEActor", RBEActorName_IDD_d)
    RBEActor_IDD_d.output_filename = "test_rbe-" + RBEActorName_IDD_d + ".mhd"
    RBEActor_IDD_d.attached_to = phantom_off.name
    RBEActor_IDD_d.size = [512, 512, 365]
    # RBEActor_IDD_d.spacing = spacing
    RBEActor_IDD_d.score_in = "material"
    RBEActor_IDD_d.hit_type = "random"
    RBEActor_IDD_d.model = "LEM1lda"  # mMKM LEM1lda
    # RBEActor_IDD_d.lookup_table_path = '/home/fava/opengate_refactored/opengate/tests/data/NIRS_MKM_reduced_data.txt'
    RBEActor_IDD_d.lookup_table_path = "/home/fava/opengate_refactored/opengate/tests/data/output_ref/test087/mkm_nirs_LQparameters_SURVIVAL.csv"
    RBEActor_IDD_d.cell_type = "HSG"
    RBEActor_IDD_d.r_nucleus = 3.9

    sim.physics_manager.set_max_step_size(phantom_off.name, 0.8)
    sim.physics_manager.set_production_cut("world", "all", 1000 * km)

    # doseActorName_IDD_d = "dose-1"
    # doseIDD = sim.add_actor("DoseActor", doseActorName_IDD_d)
    # doseIDD.output_filename = doseActorName_IDD_d + ".mhd"
    # doseIDD.attached_to = phantom_off
    # doseIDD.size = size
    # doseIDD.spacing = spacing
    # doseIDD.hit_type = "random"
    # doseIDD.dose.active = True

    # doseActorName_IDD_d_2 = "dose-2"
    # doseIDD_2 = sim.add_actor("DoseActor", doseActorName_IDD_d_2)
    # doseIDD_2.output_filename = doseActorName_IDD_d_2 + ".mhd"
    # doseIDD_2.attached_to = phantom_off
    # doseIDD_2.size = size
    # doseIDD_2.spacing = spacing
    # doseIDD_2.hit_type = "random"
    # doseIDD_2.dose.active = True

    # doseActorName_IDD_d_3 = "dose-3"
    # doseIDD_3 = sim.add_actor("DoseActor", doseActorName_IDD_d_3)
    # doseIDD_3.output_filename = doseActorName_IDD_d_3 + ".mhd"
    # doseIDD_3.attached_to = phantom_off
    # doseIDD_3.size = size
    # doseIDD_3.spacing = spacing
    # doseIDD_3.hit_type = "random"
    # doseIDD_3.dose.active = True

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    # start simulation
    sim.run()

    # print results at the end
    print(stats)

    # ----------------------------------------------------------------------------------------------------------------

    # # analyze RBE dose
    # fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    # rbe_dose_img = RBEActor_IDD_d.rbe_dose_image.image
    # #dose_img = doseIDD.dose.merged_data.data[0].image
    # alpha_mix_img = RBEActor_IDD_d.alpha_mix.merged_data.quotient.image
    # utility.plot_img_axis(ax,rbe_dose_img,'RBE dose',axis='x')

    # # fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    # # utility.plot_img_axis(ax,dose_img,'Dose',axis='x')

    # fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    # utility.plot_img_axis(ax,alpha_mix_img,'alpha mix',axis='x')

    # fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(25, 10))
    # rbe_img = RBEActor_IDD_d.rbe_image.image
    # utility.plot_img_axis(ax,rbe_img,'RBE',axis='x')

    # plt.show()

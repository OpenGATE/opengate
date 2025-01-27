#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility
import pandas as pd

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "test_087")
    print(paths)
    ref_path = paths.output_ref / "test087"
    mkm_lq_fpath = ref_path / "mkm_nirs_LQparameters_SURVIVAL.csv"
    #    df = pd.read_csv(mkm_lq_fpath)
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 12345678910
    ui.number_of_threads = 16

    numPartSimTest = 40000 / ui.number_of_threads
    numPartSimRef = 1e4

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
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
    phantom_off = sim.add_volume("Box", "phantom_off")
    phantom_off.mother = phantom.name
    phantom_off.size = [100 * mm, 10 * mm, 10 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    phantom_off.material = test_material_name
    phantom_off.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 1424 * MeV
    # source.energy.type = 'gauss'
    # source.energy.sigma_gauss = 1 * MeV
    source.particle = "ion 6 12"
    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.radius = 4 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    # print(dir(source.energy))
    source.n = numPartSimTest
    # source.activity = 100 * kBq

    size = [50, 1, 1]
    spacing = [2.0 * mm, 60.0 * mm, 60.0 * mm]

    doseActorName_IDD_d = "IDD_d"
    doseIDD = sim.add_actor("DoseActor", doseActorName_IDD_d)
    doseIDD.output_filename = paths.output / ("test087-" + doseActorName_IDD_d + ".mhd")
    print(f'actor: {paths.output / ("test087-" + doseActorName_IDD_d + ".mhd")}')
    doseIDD.attached_to = phantom_off.name
    doseIDD.size = size
    doseIDD.spacing = spacing
    doseIDD.hit_type = "random"
    doseIDD.dose.active = False
    #
    #    RBE = "RBE"
    #    RBE_act = sim.add_actor("BeamQualityActor", RBE)
    #    RBE_act.output_filename = paths.output / ("test087-" + RBE + ".mhd")
    #    RBE_act.attached_to = phantom_off.name
    #    RBE_act.size = size
    #    RBE_act.spacing = spacing
    #    RBE_act.hit_type = "random"
    ##    RBE_act.other_material = 'G4_Alanine'
    #    # both lines do the same thing,
    ##    RBE_act.dose_average = False
    ##    RBE_act.enable_rbe = True
    ##    RBE_act.is_energy_per_nucleon = False
    ##    RBE_act.fclin = 1.0
    ##    RBE_act.lookup_table_path = (
    ##        "/opt/GATE/GateRTion-1.1/install/data/RE_Alanine/RE_Alanine_RBEstyle.txt"
    ##    )
    ##    RBE_act.lookup_table_path = (
    ##        "/home/ideal/0_Data/21_RBE/01_Tables/NIRS_MKM_reduced_data.txt"
    ##    )
    #    RBE_act.lookup_table_path = ref_path / "RE_Alanine_RBEstyle.txt"

    RBE = "RBE"
    RBE_act = sim.add_actor("RBEActor", "RBE_act")
    RBE_act.output_filename = paths.output / ("test087-" + RBE + ".mhd")
    RBE_act.attached_to = phantom_off.name
    RBE_act.size = size
    RBE_act.spacing = spacing
    RBE_act.hit_type = "random"
    RBE_act.model = "mMKM"
    #    RBE_act.model = "LEM1lda"
    #    RBE_act.score_in = "G4_WATER"

    #    RBE_act.lookup_table_path = mkm_lq_fpath
    RBE_act.lookup_table_path = "/users/aresch/Documents/RBE/NIRS_MKM_reduced_data.txt"
    #    RBE_act.lookup_table_path = '/users/aresch/Documents/RBE/LEM1_RS.txt'
    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True

    sim.run()

    # ----------------------------------------------------------------------------------------------------------------
    print(RBE_act)

    fNameIDD = doseIDD.user_info.output
    """
    is_ok = utility.assert_images(
        ref_path / fNameIDD,
        doseIDD.output,
        stat,
        tolerance=100,
        ignore_value=0,
        axis="x",
        scaleImageValuesFactor=numPartSimRef / numPartSimTest,
    )

    """
    ref_fpath = ref_path / "test087-RBE_rbe.mhd"
    print(f"{doseIDD.dose.get_output_path()=}")
    is_ok = utility.assert_filtered_imagesprofile1D(
        ref_filter_filename1=doseIDD.edep.get_output_path(),
        ref_filename1=ref_fpath,
        filename2=paths.output / RBE_act.rbe.get_output_path(),
        tolerance=20,
        eval_quantity="RBE",
        #        plt_ylim=[0, 2],
    )

    # )
    # is_ok = (
    #     utility.assert_filtered_imagesprofile1D(
    #         ref_filter_filename1=ref_path / fNameIDD,
    #         ref_filename1=ref_path / "test050_LET1D_Z1__PrimaryProton-doseAveraged.mhd",
    #         filename2=paths.output / LETActor_primaries.user_info.output,
    #         tolerance=8,
    #         plt_ylim=[0, 25],
    #     )
    #     and is_ok
    # )

    utility.test_ok(is_ok)

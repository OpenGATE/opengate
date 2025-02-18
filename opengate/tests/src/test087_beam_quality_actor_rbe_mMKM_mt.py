#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "test_087")

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
    ui.number_of_threads = 8

    numPartSimTest = 4e2 / ui.number_of_threads
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

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [50 * mm, 10 * cm, 10 * cm]
    phantom.translation = [-25 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    test_material_name = "G4_WATER"
    phantom_off = sim.add_volume("Box", "phantom_off")
    phantom_off.mother = phantom.name
    phantom_off.size = [50 * mm, 10 * mm, 10 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    phantom_off.material = test_material_name
    phantom_off.color = [0, 0, 1, 1]

    sim.physics_manager.physics_list_name = "FTFP_INCLXX_EMZ"

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 1424 * MeV
    source.particle = "ion 6 12"
    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.radius = 4 * mm
    source.position.translation = [0 * mm, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    source.n = numPartSimTest

    size = [50, 1, 1]
    spacing = [1.0 * mm, 100.0 * mm, 100.0 * mm]

    doseActorName_IDD_d = "IDD_d"
    doseIDD = sim.add_actor("DoseActor", doseActorName_IDD_d)
    doseIDD.output_filename = paths.output / ("test087-" + doseActorName_IDD_d + ".mhd")
    #    print(f'actor: {paths.output / ("test087-" + doseActorName_IDD_d + ".mhd")}')
    doseIDD.attached_to = phantom_off.name
    doseIDD.size = size
    doseIDD.spacing = spacing
    doseIDD.hit_type = "random"
    doseIDD.dose.active = False

    RBE = "RBE"
    RBE_act = sim.add_actor("RBEActor", "RBE_act")
    RBE_act.output_filename = paths.output / ("test087-" + RBE + ".mhd")
    RBE_act.attached_to = phantom_off.name
    RBE_act.size = size
    RBE_act.spacing = spacing
    RBE_act.hit_type = "random"
    RBE_act.model = "mMKM"
    RBE_act.r_nucleus = 3.9
    #    RBE_act.model = "LEM1lda"

    RBE_act.energy_per_nucleon = False
    RBE_act.lookup_table_path = mkm_lq_fpath

    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True

    sim.run()

    ref_fpath = ref_path / "test087-ref_rbe.mhd"
    #    print(f"{doseIDD.dose.get_output_path()=}")

    is_ok = utility.assert_filtered_imagesprofile1D(
        ref_filter_filename1=doseIDD.edep.get_output_path(),
        ref_filename1=ref_fpath,
        filename2=paths.output / RBE_act.rbe.get_output_path(),
        tolerance=20,
        eval_quantity="RBE",
        #        plt_ylim=[0, 2],
    )

    ref_fpath = ref_path / "test087-ref_alpha_mix.mhd"

    fName = paths.output / RBE_act.alpha_mix.get_output_path()

    is_ok = is_ok and utility.assert_filtered_imagesprofile1D(
        ref_filter_filename1=doseIDD.edep.get_output_path(),
        ref_filename1=ref_fpath,
        filename2=paths.output / RBE_act.alpha_mix.get_output_path(),
        tolerance=20,
        eval_quantity="alpha",
    )

    utility.test_ok(is_ok)

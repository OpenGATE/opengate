#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect.ge_discovery_nm670 as nm670
from opengate.userhooks import check_production_cuts
from opengate.tests import utility


def create_spect_simu(sim, paths, number_of_threads=1):
    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "qt"
    sim.number_of_threads = number_of_threads
    sim.random_seed = 12345678
    # sim.random_seed = "auto"
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    # world size
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    # spect head (debug mode = very small collimator)
    spect, colli, crystal = nm670.add_spect_head(
        sim, "spect", collimator_type=False, debug=False
    )
    nm670.rotate_gantry(spect, 20 * cm, 0)

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [15 * cm, 15 * cm, 15 * cm]
    waterbox.material = "G4_WATER"
    blue = [0, 1, 1, 1]
    waterbox.color = blue

    # physic list
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = False

    sim.physics_manager.global_production_cuts.gamma = 10 * mm
    sim.physics_manager.global_production_cuts.electron = 10 * mm
    sim.physics_manager.global_production_cuts.positron = 10 * mm
    sim.physics_manager.global_production_cuts.proton = 10 * mm

    sim.physics_manager.set_production_cut(
        volume_name="spect",
        particle_name="gamma",
        value=0.1 * mm,
    )
    sim.physics_manager.set_production_cut(
        volume_name="spect",
        particle_name="electron",
        value=0.01 * mm,
    )
    sim.physics_manager.set_production_cut(
        volume_name="spect",
        particle_name="positron",
        value=0.1 * mm,
    )

    # default source for tests
    activity = 30 * kBq
    beam1 = sim.add_source("GenericSource", "beam1")
    beam1.attached_to = waterbox.name
    beam1.particle = "gamma"
    beam1.energy.mono = 140.5 * keV
    beam1.position.type = "sphere"
    beam1.position.radius = 3 * cm
    beam1.position.translation = [0, 0, 0 * cm]
    beam1.direction.type = "momentum"
    beam1.direction.momentum = [0, 1, 0]
    # beam1.direction.type = 'iso'
    beam1.activity = activity / sim.number_of_threads

    beam2 = sim.add_source("GenericSource", "beam2")
    beam2.attached_to = waterbox.name
    beam2.particle = "gamma"
    beam2.energy.mono = 140.5 * keV
    beam2.position.type = "sphere"
    beam2.position.radius = 3 * cm
    beam2.position.translation = [18 * cm, 0, 0]
    beam2.direction.type = "momentum"
    beam2.direction.momentum = [0, 1, 0]
    # beam2.direction.type = 'iso'
    beam2.activity = activity / sim.number_of_threads

    beam3 = sim.add_source("GenericSource", "beam3")
    beam3.attached_to = waterbox.name
    beam3.particle = "gamma"
    beam3.energy.mono = 140.5 * keV
    beam3.position.type = "sphere"
    beam3.position.radius = 1 * cm
    beam3.position.translation = [0, 10 * cm, 0]
    beam3.direction.type = "momentum"
    beam3.direction.momentum = [0, 1, 0]
    # beam3.direction.type = 'iso'
    beam3.activity = activity / sim.number_of_threads

    # add stat actor
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats_actor.track_types_flag = True
    stats_actor.output_filename = "stats.txt"

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    # get crystal volume by looking for the word crystal in the name
    for k, v in sim.volume_manager.volumes.items():
        if "crystal" in k:
            crystal = v
    hc.attached_to = crystal.name
    print("Crystal :", crystal.name)
    hc.output_filename = "test028.root"
    print(hc.output_filename)
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "TrackVolumeCopyNo",
        "PostStepUniqueVolumeID",
        "PreStepUniqueVolumeID",
        "GlobalTime",
        "KineticEnergy",
        "ProcessDefinedStep",
    ]

    # singles collection
    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.attached_to = crystal.name
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWinnerPosition"
    # sc.policy = 'EnergyWeightedCentroidPosition'
    sc.skip_attributes = ["KineticEnergy", "ProcessDefinedStep"]
    sc.output_filename = hc.output_filename

    # EnergyWindows
    cc = sim.add_actor("DigitizerEnergyWindowsActor", "EnergyWindows")
    cc.attached_to = crystal.name
    cc.input_digi_collection = "Singles"
    cc.channels = [
        {"name": "scatter", "min": 114 * keV, "max": 126 * keV},
        {"name": "peak140", "min": 126 * keV, "max": 154.55 * keV},
        {
            "name": "spectrum",
            "min": 0 * keV,
            "max": 5000 * keV,
        },  # should be strictly equal to 'Singles'
    ]
    cc.output_filename = hc.output_filename

    """
        The order of the actors is important !
        1. Hits
        2. Singles
        3. EnergyWindows
    """

    # sec = gate.g4_units.second
    # sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1 * sec]]

    # user hook function
    sim.user_hook_after_init = check_production_cuts

    return spect


def test_add_proj(sim):
    mm = gate.g4_units.mm
    crystal = None
    for k, v in sim.volume_manager.volumes.items():
        if "crystal" in k:
            crystal = v
    # 2D binning projection
    proj = sim.add_actor("DigitizerProjectionActor", "Projection")
    proj.attached_to = crystal.name
    # we set two times the spectrum channel to compare with Gate output
    proj.input_digi_collections = ["spectrum", "scatter", "peak140", "spectrum"]
    proj.spacing = [4.41806 * mm, 4.41806 * mm]
    proj.size = [128, 128]
    proj.output_filename = f"proj028.mhd"
    # by default, the origin of the images are centered
    # set to False here to keep compatible with previous version
    # proj.origin_as_image_center = False
    return proj


def test_spect_root(sim, paths):
    # stat
    gate.exception.warning("Compare stats")
    stats = sim.get_actor("Stats")
    print(stats)
    stats_ref = utility.read_stats_file(paths.output_ref / "stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.07)

    # Compare root files
    print()
    gate.exception.warning("Compare hits")
    ref_file = paths.output_ref / "test028.root"
    hc_file = sim.get_actor("Hits").get_output_path()
    print(ref_file, hc_file)
    checked_keys = [
        {"k1": "PostPosition_X", "k2": "PostPosition_X", "tol": 1.7, "scaling": 1},
        {"k1": "PostPosition_Y", "k2": "PostPosition_Y", "tol": 1.3, "scaling": 1},
        {"k1": "PostPosition_Z", "k2": "PostPosition_Z", "tol": 0.9, "scaling": 1},
        {
            "k1": "TotalEnergyDeposit",
            "k2": "TotalEnergyDeposit",
            "tol": 0.001,
            "scaling": 1,
        },
        {"k1": "GlobalTime", "k2": "GlobalTime", "tol": 1.5e7, "scaling": 1},
    ]
    is_ok = (
        utility.compare_root2(
            ref_file,
            hc_file,
            "Hits",
            "Hits",
            checked_keys,
            paths.output / "test028_hits.png",
            n_tol=4,
        )
        and is_ok
    )

    # Compare root files
    print()
    gate.exception.warning("Compare singles")
    hc_file = sim.get_actor("Singles").get_output_path()
    checked_keys = [
        {"k1": "PostPosition_X", "k2": "PostPosition_X", "tol": 1.8, "scaling": 1},
        {"k1": "PostPosition_Y", "k2": "PostPosition_Y", "tol": 1.3, "scaling": 1},
        {"k1": "PostPosition_Z", "k2": "PostPosition_Z", "tol": 0.6, "scaling": 1},
        {
            "k1": "TotalEnergyDeposit",
            "k2": "TotalEnergyDeposit",
            "tol": 0.001,
            "scaling": 1,
        },
    ]
    is_ok = (
        utility.compare_root2(
            ref_file,
            hc_file,
            "Singles",
            "Singles",
            checked_keys,
            paths.output / "test028_singles.png",
        )
        and is_ok
    )

    # Compare root files
    print()
    gate.exception.warning("Compare singles and spectrum (must be strictly equal)")
    ref_file = sim.get_actor("Singles").get_output_path()
    hc_file = sim.get_actor("EnergyWindows").get_output_path()
    checked_keys = [
        {"k1": "PostPosition_X", "k2": "PostPosition_X", "tol": 0.001, "scaling": 1},
        {"k1": "PostPosition_Y", "k2": "PostPosition_Y", "tol": 0.001, "scaling": 1},
        {"k1": "PostPosition_Z", "k2": "PostPosition_Z", "tol": 0.001, "scaling": 1},
        {
            "k1": "TotalEnergyDeposit",
            "k2": "TotalEnergyDeposit",
            "tol": 0.001,
            "scaling": 1,
        },
    ]
    is_ok = (
        utility.compare_root2(
            ref_file,
            hc_file,
            "Singles",
            "spectrum",
            checked_keys,
            paths.output / "test028_spectrum.png",
            n_tol=0.01,
        )
        and is_ok
    )

    # Compare root files
    print()
    gate.exception.warning("Compare scatter")
    ref_file = paths.output_ref / "test028.root"
    hc_file = sim.get_actor("EnergyWindows").get_output_path()
    checked_keys = [
        {"k1": "PostPosition_X", "k2": "PostPosition_X", "tol": 13, "scaling": 1},
        {"k1": "PostPosition_Y", "k2": "PostPosition_Y", "tol": 5, "scaling": 1},
        {"k1": "PostPosition_Z", "k2": "PostPosition_Z", "tol": 8, "scaling": 1},
        {
            "k1": "TotalEnergyDeposit",
            "k2": "TotalEnergyDeposit",
            "tol": 0.2,
            "scaling": 1,
        },
    ]
    is_ok = (
        utility.compare_root2(
            ref_file,
            hc_file,
            "scatter",
            "scatter",
            checked_keys,
            paths.output / "test028_scatter.png",
            n_tol=15,
        )
        and is_ok
    )

    # Compare root files
    print()
    gate.exception.warning("Compare peak")
    ref_file = paths.output_ref / "test028.root"
    hc_file = sim.get_actor("EnergyWindows").get_output_path()
    checked_keys = [
        {"k1": "PostPosition_X", "k2": "PostPosition_X", "tol": 1.1, "scaling": 1},
        {"k1": "PostPosition_Y", "k2": "PostPosition_Y", "tol": 0.4, "scaling": 1},
        {"k1": "PostPosition_Z", "k2": "PostPosition_Z", "tol": 0.4, "scaling": 1},
        {
            "k1": "TotalEnergyDeposit",
            "k2": "TotalEnergyDeposit",
            "tol": 0.1,
            "scaling": 1,
        },
    ]
    is_ok = (
        utility.compare_root2(
            ref_file,
            hc_file,
            "peak140",
            "peak140",
            checked_keys,
            paths.output / "test028_peak.png",
            n_tol=2.1,
        )
        and is_ok
    )

    return is_ok


def test_spect_proj(sim, paths, proj, output_ref_folder=None, output_ref_filename=None):
    print()
    stats = sim.get_actor("Stats")
    stats.user_output.stats.merged_data.runs = 1  # force to 1 to compare with MT
    print(stats)
    if output_ref_folder is None:
        output_ref_folder = paths.output_ref
    stats_ref = utility.read_stats_file(output_ref_folder / "stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.025)

    # compare images with Gate
    print()
    print("Compare images with ref")
    fn = proj.get_output_path("counts")
    if output_ref_filename is None:
        output_ref_filename = paths.output_ref / fn.name
    print(fn)
    print(output_ref_filename)
    is_ok = (
        utility.assert_images(
            output_ref_folder / output_ref_filename,
            fn,
            stats,
            tolerance=16,
            ignore_value_data2=0,
            axis="x",
            fig_name=paths.output / f"{fn.stem}.png",
            sum_tolerance=6,
        )
        and is_ok
    )
    return is_ok

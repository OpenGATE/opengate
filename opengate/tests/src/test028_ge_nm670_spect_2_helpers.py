#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect_ge_nm670 as gate_spect
import itk
import numpy as np

from opengate.user_hooks import check_production_cuts


def create_spect_simu(sim, paths, number_of_threads=1):
    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.number_of_threads = number_of_threads
    ui.random_seed = 123456

    # units
    m = gate.g4_units("m")
    cm = gate.g4_units("cm")
    keV = gate.g4_units("keV")
    mm = gate.g4_units("mm")
    Bq = gate.g4_units("Bq")
    kBq = 1000 * Bq

    # world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_AIR"

    # spect head (debug mode = very small collimator)
    spect, crystal = gate_spect.add_ge_nm67_spect_head(
        sim, "spect", collimator_type=False, debug=False
    )
    psd = 6.11 * cm
    spect.translation = [0, 0, -(20 * cm + psd)]

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [15 * cm, 15 * cm, 15 * cm]
    waterbox.material = "G4_WATER"
    blue = [0, 1, 1, 1]
    waterbox.color = blue

    # physic list
    p = sim.get_physics_user_info()
    p.physics_list_name = "G4EmStandardPhysics_option4"
    p.enable_decay = False

    sim.physics_manager.global_production_cuts.gamma = 10 * mm
    sim.physics_manager.global_production_cuts.electron = 10 * mm
    sim.physics_manager.global_production_cuts.positron = 10 * mm
    sim.physics_manager.global_production_cuts.proton = 10 * mm

    sim.set_production_cut(
        volume_name="spect",
        particle_name="gamma",
        value=0.1 * mm,
    )
    sim.set_production_cut(
        volume_name="spect",
        particle_name="electron",
        value=0.01 * mm,
    )
    sim.set_production_cut(
        volume_name="spect",
        particle_name="positron",
        value=0.1 * mm,
    )

    # cuts = p.production_cuts
    # cuts.world.gamma = 10 * mm
    # cuts.world.electron = 10 * mm
    # cuts.world.positron = 10 * mm
    # cuts.world.proton = 10 * mm

    # cuts.spect.gamma = 0.1 * mm
    # cuts.spect.electron = 0.01 * mm
    # cuts.spect.positron = 0.1 * mm

    # default source for tests
    activity = 30 * kBq
    beam1 = sim.add_source("GenericSource", "beam1")
    beam1.mother = waterbox.name
    beam1.particle = "gamma"
    beam1.energy.mono = 140.5 * keV
    beam1.position.type = "sphere"
    beam1.position.radius = 3 * cm
    beam1.position.translation = [0, 0, 0 * cm]
    beam1.direction.type = "momentum"
    beam1.direction.momentum = [0, 0, -1]
    # beam1.direction.type = 'iso'
    beam1.activity = activity / ui.number_of_threads

    beam2 = sim.add_source("GenericSource", "beam2")
    beam2.mother = waterbox.name
    beam2.particle = "gamma"
    beam2.energy.mono = 140.5 * keV
    beam2.position.type = "sphere"
    beam2.position.radius = 3 * cm
    beam2.position.translation = [18 * cm, 0, 0]
    beam2.direction.type = "momentum"
    beam2.direction.momentum = [0, 0, -1]
    # beam2.direction.type = 'iso'
    beam2.activity = activity / ui.number_of_threads

    beam3 = sim.add_source("GenericSource", "beam3")
    beam3.mother = waterbox.name
    beam3.particle = "gamma"
    beam3.energy.mono = 140.5 * keV
    beam3.position.type = "sphere"
    beam3.position.radius = 1 * cm
    beam3.position.translation = [0, 10 * cm, 0]
    beam3.direction.type = "momentum"
    beam3.direction.momentum = [0, 0, -1]
    # beam3.direction.type = 'iso'
    beam3.activity = activity / ui.number_of_threads

    # add stat actor
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats_actor.track_types_flag = True

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    # get crystal volume by looking for the word crystal in the name
    l = sim.get_all_volumes_user_info()
    crystal = l[[k for k in l if "crystal" in k][0]]
    hc.mother = crystal.name
    print("Crystal :", crystal.name)
    hc.output = paths.output / "test028.root"
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
    sc.mother = crystal.name
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWinnerPosition"
    # sc.policy = 'EnergyWeightedCentroidPosition'
    sc.skip_attributes = ["KineticEnergy", "ProcessDefinedStep", "KineticEnergy"]
    sc.output = hc.output

    # EnergyWindows
    cc = sim.add_actor("DigitizerEnergyWindowsActor", "EnergyWindows")
    cc.mother = crystal.name
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
    cc.output = hc.output

    """
        The order of the actors is important !
        1. Hits
        2. Singles
        3. EnergyWindows
    """

    # sec = gate.g4_units('second')
    # sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1 * sec]]

    # user hook function
    sim.user_fct_after_init = check_production_cuts

    return spect


def test_add_proj(sim, paths):
    mm = gate.g4_units("mm")
    l = sim.get_all_volumes_user_info()
    crystal = l[[k for k in l if "crystal" in k][0]]
    # 2D binning projection
    proj = sim.add_actor("DigitizerProjectionActor", "Projection")
    proj.mother = crystal.name
    # we set two times the spectrum channel to compare with Gate output
    proj.input_digi_collections = ["spectrum", "scatter", "peak140", "spectrum"]
    proj.spacing = [4.41806 * mm, 4.41806 * mm]
    proj.size = [128, 128]
    # proj.plane = 'XY' # not implemented yet # FIXME
    proj.output = paths.output / "proj028.mhd"
    # by default, the origin of the images are centered
    # set to False here to keep compatible with previous version
    proj.origin_as_image_center = False
    return proj


def test_spect_hits(output, paths, version="2"):
    # stat
    gate.warning("Compare stats")
    stats = output.get_actor("Stats")
    print(stats)
    print(f"Number of runs was {stats.counts.run_count}. Set to 1 before comparison")
    stats.counts.run_count = 1  # force to 1
    stats_ref = gate.read_stat_file(paths.gate_output / f"stat{version}.txt")
    is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.07)

    # Compare root files
    print()
    gate.warning("Compare hits")
    gate_file = paths.gate_output / f"hits{version}.root"
    hc_file = output.get_actor("Hits").user_info.output
    print(hc_file)
    checked_keys = [
        {"k1": "posX", "k2": "PostPosition_X", "tol": 1.7, "scaling": 1},
        {"k1": "posY", "k2": "PostPosition_Y", "tol": 1.3, "scaling": 1},
        {"k1": "posZ", "k2": "PostPosition_Z", "tol": 0.9, "scaling": 1},
        {"k1": "edep", "k2": "TotalEnergyDeposit", "tol": 0.001, "scaling": 1},
        {"k1": "time", "k2": "GlobalTime", "tol": 0.01, "scaling": 1e-9},
    ]
    is_ok = (
        gate.compare_root2(
            gate_file,
            hc_file,
            "Hits",
            "Hits",
            checked_keys,
            paths.output / f"test028_{version}_hits.png",
            n_tol=4,
        )
        and is_ok
    )

    # Compare root files
    print()
    gate.warning("Compare singles")
    gate_file = paths.gate_output / f"hits{version}.root"
    hc_file = output.get_actor("Singles").user_info.output
    checked_keys = [
        {"k1": "globalPosX", "k2": "PostPosition_X", "tol": 1.8, "scaling": 1},
        {"k1": "globalPosY", "k2": "PostPosition_Y", "tol": 1.3, "scaling": 1},
        {"k1": "globalPosZ", "k2": "PostPosition_Z", "tol": 0.2, "scaling": 1},
        {"k1": "energy", "k2": "TotalEnergyDeposit", "tol": 0.001, "scaling": 1},
    ]
    is_ok = (
        gate.compare_root2(
            gate_file,
            hc_file,
            "Singles",
            "Singles",
            checked_keys,
            paths.output / f"test028_{version}_singles.png",
        )
        and is_ok
    )

    # Compare root files
    print()
    gate.warning("Compare singles and spectrum (must be strictly equal)")
    ref_file = output.get_actor("Singles").user_info.output
    hc_file = output.get_actor("EnergyWindows").user_info.output
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
        gate.compare_root2(
            ref_file,
            hc_file,
            "Singles",
            "spectrum",
            checked_keys,
            paths.output / f"test028_{version}_spectrum.png",
            n_tol=0.01,
        )
        and is_ok
    )

    # Compare root files
    print()
    gate.warning("Compare scatter")
    hc_file = output.get_actor("EnergyWindows").user_info.output
    checked_keys = [
        {"k1": "globalPosX", "k2": "PostPosition_X", "tol": 20, "scaling": 1},
        {"k1": "globalPosY", "k2": "PostPosition_Y", "tol": 15, "scaling": 1},
        {"k1": "globalPosZ", "k2": "PostPosition_Z", "tol": 1.8, "scaling": 1},
        {"k1": "energy", "k2": "TotalEnergyDeposit", "tol": 0.2, "scaling": 1},
    ]
    is_ok = (
        gate.compare_root2(
            gate_file,
            hc_file,
            "scatter",
            "scatter",
            checked_keys,
            paths.output / f"test028_{version}_scatter.png",
            n_tol=15,
        )
        and is_ok
    )

    # Compare root files
    print()
    gate.warning("Compare peak")
    hc_file = output.get_actor("EnergyWindows").user_info.output
    checked_keys = [
        {"k1": "globalPosX", "k2": "PostPosition_X", "tol": 1.7, "scaling": 1},
        {"k1": "globalPosY", "k2": "PostPosition_Y", "tol": 1, "scaling": 1},
        {"k1": "globalPosZ", "k2": "PostPosition_Z", "tol": 0.21, "scaling": 1},
        {"k1": "energy", "k2": "TotalEnergyDeposit", "tol": 0.1, "scaling": 1},
    ]
    is_ok = (
        gate.compare_root2(
            gate_file,
            hc_file,
            "peak140",
            "peak140",
            checked_keys,
            paths.output / f"test028_{version}_peak.png",
            n_tol=2.1,
        )
        and is_ok
    )

    return is_ok


def test_spect_proj(output, paths, proj, version="3"):
    print()
    stats = output.get_actor("Stats")
    stats.counts.run_count = 1  # force to 1 to compare with gate result
    print(stats)
    stats_ref = gate.read_stat_file(paths.gate_output / f"stat{version}.txt")
    is_ok = gate.assert_stats(stats, stats_ref, 0.025)

    # compare images with Gate
    print()
    print("Compare images (old spacing/origin)")
    # read image and force change the offset to be similar to old Gate
    img = itk.imread(str(paths.output / "proj028.mhd"))
    spacing = np.array(proj.user_info.spacing)
    origin = spacing / 2.0
    origin[2] = 0.5
    spacing[2] = 1
    img.SetSpacing(spacing)
    img.SetOrigin(origin)
    itk.imwrite(img, str(paths.output / "proj028_offset.mhd"))
    is_ok = (
        gate.assert_images(
            paths.gate_output / f"projection{version}.mhd",
            paths.output / "proj028_offset.mhd",
            stats,
            tolerance=16,
            ignore_value=0,
            axis="y",
            sum_tolerance=1.6,
            fig_name=paths.output / f"proj028_{version}_offset.png",
        )
        and is_ok
    )

    # compare images with Gate
    if version == "3_blur":
        return is_ok
    print()
    print("Compare images (new spacing/origin")
    # read image and force change the offset to be similar to old Gate
    is_ok = (
        gate.assert_images(
            paths.output_ref / "proj028_ref.mhd",
            paths.output / "proj028.mhd",
            stats,
            tolerance=14,
            ignore_value=0,
            axis="y",
            sum_tolerance=1.5,
            fig_name=paths.output / f"proj028_{version}_no_offset.png",
        )
        and is_ok
    )

    return is_ok

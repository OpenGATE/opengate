#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import opengate.contrib.spect.genm670 as gate_spect
import itk
import numpy as np

paths = utility.get_default_test_paths(__file__, "gate_test028_ge_nm670_spect")


def create_spect_simu(
    sim,
    paths,
    number_of_threads=1,
    activity_kBq=300,
    aa_enabled=True,
    aa_mode="SkipEnergy",
):
    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.number_of_threads = number_of_threads
    ui.check_volumes_overlap = False
    ui.random_engine = "MixMaxRng"
    ui.random_seed = 123456789

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    # world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_AIR"

    # spect head (debug mode = very small collimator)
    spect, crystal = gate_spect.add_ge_nm67_spect_head(
        sim, "spect", collimator_type="lehr", debug=False
    )

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [15 * cm, 15 * cm, 15 * cm]
    waterbox.material = "G4_WATER"
    waterbox.translation = [0, 0, 0]
    blue = [0, 1, 1, 1]
    waterbox.color = blue

    # physic list
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = False

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
        value=0.1 * mm,
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
    # cuts.spect.electron = 0.1 * mm
    # cuts.spect.positron = 0.1 * mm

    # default source for tests
    # activity = 300 * kBq
    activity = activity_kBq * kBq
    beam1 = sim.add_source("GenericSource", "beam1")
    beam1.mother = waterbox.name
    beam1.particle = "gamma"
    beam1.energy.mono = 140.5 * keV
    beam1.position.type = "sphere"
    beam1.position.radius = 1 * cm
    beam1.position.translation = [0, 0, 0]
    beam1.direction.type = "iso"
    if aa_enabled:
        beam1.direction.acceptance_angle.volumes = ["spect"]
        beam1.direction.acceptance_angle.intersection_flag = True
        beam1.direction.acceptance_angle.skip_policy = aa_mode
    beam1.activity = activity / ui.number_of_threads

    beam2 = sim.add_source("GenericSource", "beam2")
    beam2.mother = waterbox.name
    beam2.particle = "gamma"
    beam2.energy.mono = 140.5 * keV
    beam2.position.type = "sphere"
    beam2.position.radius = 3 * cm
    beam2.position.translation = [18 * cm, 0, 0]
    beam2.direction.type = "iso"
    if aa_enabled:
        beam2.direction.acceptance_angle.volumes = ["spect"]
        beam2.direction.acceptance_angle.intersection_flag = True
        beam2.direction.acceptance_angle.skip_policy = aa_mode
    beam2.activity = activity / ui.number_of_threads

    beam3 = sim.add_source("GenericSource", "beam3")
    beam3.mother = waterbox.name
    beam3.particle = "gamma"
    beam3.energy.mono = 140.5 * keV
    beam3.position.type = "sphere"
    beam3.position.radius = 1 * cm
    beam3.position.translation = [0, 10 * cm, 0]
    beam3.direction.type = "iso"
    if aa_enabled:
        beam3.direction.acceptance_angle.volumes = ["spect"]
        beam3.direction.acceptance_angle.intersection_flag = True
        beam3.direction.acceptance_angle.skip_policy = aa_mode
    beam3.activity = activity / ui.number_of_threads

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    # get crystal volume by looking for the word crystal in the name
    l = sim.get_all_volumes_user_info()
    crystal = l[[k for k in l if "crystal" in k][0]]
    hc.mother = crystal.name
    hc.output = ""  # No output paths.output / 'test028.root'
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PostStepUniqueVolumeID",
        "PreStepUniqueVolumeID",
        "GlobalTime",
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
        # {'name': 'spectrum', 'min': 0 * keV, 'max': 5000 * keV}  # should be strictly equal to 'Singles'
    ]
    cc.output = hc.output

    # projection
    l = sim.get_all_volumes_user_info()
    crystal = l[[k for k in l if "crystal" in k][0]]
    # 2D binning projection
    proj = sim.add_actor("DigitizerProjectionActor", "Projection")
    proj.mother = crystal.name
    # we set two times the spectrum channel to compare with Gate output
    proj.input_digi_collections = ["Singles", "scatter", "peak140", "Singles"]
    proj.spacing = [4.41806 * mm, 4.41806 * mm]
    proj.size = [128, 128]
    # proj.plane = 'XY' # not implemented yet
    proj.output = paths.output / "proj028_colli.mhd"

    # rotate spect
    cm = gate.g4_units.cm
    psd = 6.11 * cm
    p = [0, 0, -(15 * cm + psd)]
    spect.translation, spect.rotation = gate.geometry.utility.get_transform_orbiting(
        p, "y", 15
    )
    print("rotation 15 deg and translation = ", spect.translation)

    return spect, proj


def compare_result(output, proj, fig_name, sum_tolerance=8):
    gate.exception.warning("Compare acceptance angle skipped particles")
    stats = output.get_actor("Stats")

    reference_ratio = 691518 / 2998895  # (23%)
    b1 = gate.sources.generic.get_source_zero_events(output, "beam1")
    b2 = gate.sources.generic.get_source_zero_events(output, "beam2")
    b3 = gate.sources.generic.get_source_zero_events(output, "beam3")
    print(f"Number of zeros events: {b1} {b2} {b3}")

    print(f"Number of simulated events: {stats.counts.event_count}")
    beam1 = output.get_source("beam1")
    mode = beam1.user_info.direction.acceptance_angle.skip_policy
    stats_ref = utility.read_stat_file(paths.gate_output / "stat4.txt")

    if mode == "SkipEvents":
        b1 = gate.sources.generic.get_source_skipped_events(output, "beam1")
        b2 = gate.sources.generic.get_source_skipped_events(output, "beam2")
        b3 = gate.sources.generic.get_source_skipped_events(output, "beam3")
        stats.counts.event_count = stats.counts.event_count + b1 + b2 + b3
        print(f"Skip Events mode, adding the skipped ones")
        print(f"Number of simulated events: {stats.counts.event_count}")
        # do not compare track in this mode
        stats.counts.track_count = stats_ref.counts.track_count

    tol = 0.3
    r1 = b1 / stats.counts.event_count
    is_ok = (r1 - reference_ratio) / reference_ratio < tol
    utility.print_test(
        is_ok,
        f"Skipped particles b1 = {b1} {r1 * 100:.2f} %  vs {reference_ratio * 100:.2f} % ",
    )

    r2 = b2 / stats.counts.event_count
    is_ok = (r2 - reference_ratio) / reference_ratio < tol
    utility.print_test(
        is_ok,
        f"Skipped particles b2 = {b2} {r2 * 100:.2f} %  vs {reference_ratio * 100:.2f} % ",
    )

    r3 = b3 / stats.counts.event_count
    is_ok = (r3 - reference_ratio) / reference_ratio < tol
    utility.print_test(
        is_ok,
        f"Skipped particles b3 = {b3} {r3 * 100:.2f} %  vs {reference_ratio * 100:.2f} % ",
    )

    # stat
    gate.exception.warning("Compare stats")
    print(stats)
    print(f"Number of runs was {stats.counts.run_count}. Set to 1 before comparison")
    stats.counts.run_count = 1  # force to 1
    print(
        f"Number of steps was {stats.counts.step_count}, force to the same value (because of angle acceptance). "
    )
    stats.counts.step_count = stats_ref.counts.step_count  # force to id
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.07) and is_ok

    # read image and force change the offset to be similar to old Gate
    gate.exception.warning("Compare projection image")
    img = itk.imread(str(paths.output / "proj028_colli.mhd"))
    spacing = np.array([proj.spacing[0], proj.spacing[1], 1])
    print("spacing", spacing)
    origin = spacing / 2.0
    origin[2] = 0.5
    spacing[2] = 1
    img.SetSpacing(spacing)
    img.SetOrigin(origin)
    itk.imwrite(img, str(paths.output / "proj028_colli_offset.mhd"))
    # There are not enough event to make a proper comparison, so the tol is very high
    is_ok = (
        utility.assert_images(
            paths.gate_output / "projection4.mhd",
            paths.output / "proj028_colli_offset.mhd",
            stats,
            tolerance=83,
            ignore_value=0,
            axis="x",
            sum_tolerance=sum_tolerance,
            fig_name=str(paths.output / fig_name),
        )
        and is_ok
    )

    return is_ok

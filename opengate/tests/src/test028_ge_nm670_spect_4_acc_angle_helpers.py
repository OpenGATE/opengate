#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import opengate.contrib.spect.ge_discovery_nm670 as gate_spect
import itk
import numpy as np

paths = utility.get_default_test_paths(
    __file__, "gate_test028_ge_nm670_spect", output_folder="test028"
)


def create_spect_simu(
    sim,
    paths,
    number_of_threads=1,
    activity_kBq=300,
    aa_enabled=True,
    aa_mode="SkipEnergy",
):
    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = number_of_threads
    sim.check_volumes_overlap = False
    sim.random_engine = "MixMaxRng"
    sim.random_seed = 123456789
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
    spect, colli, crystal = gate_spect.add_spect_head(
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
    sim.physics_manager.set_production_cut(
        volume_name="world", particle_name="all", value=10 * mm
    )
    sim.physics_manager.set_production_cut(
        volume_name="spect",
        particle_name="gamma",
        value=0.1 * mm,
    )
    sim.physics_manager.set_production_cut(
        volume_name="spect",
        particle_name="electron",
        value=0.1 * mm,
    )
    sim.physics_manager.set_production_cut(
        volume_name="spect",
        particle_name="positron",
        value=0.1 * mm,
    )

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
    beam1.activity = activity / sim.number_of_threads

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
    beam2.activity = activity / sim.number_of_threads

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
    beam3.activity = activity / sim.number_of_threads

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    # get crystal volume by looking for the word crystal in the name
    for k, v in sim.volume_manager.volumes.items():
        if "crystal" in k:
            crystal = v
    hc.attached_to = crystal.name
    hc.output_filename = "test028_4.root"  # No output paths.output / 'test028.root'
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PostStepUniqueVolumeID",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # singles collection
    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.attached_to = crystal.name
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWinnerPosition"
    # sc.policy = 'EnergyWeightedCentroidPosition'
    sc.skip_attributes = ["KineticEnergy", "ProcessDefinedStep", "KineticEnergy"]
    sc.output_filename = hc.output_filename

    # EnergyWindows
    cc = sim.add_actor("DigitizerEnergyWindowsActor", "EnergyWindows")
    cc.attached_to = crystal.name
    cc.input_digi_collection = "Singles"
    cc.channels = [
        {"name": "scatter", "min": 114 * keV, "max": 126 * keV},
        {"name": "peak140", "min": 126 * keV, "max": 154.55 * keV},
        # {'name': 'spectrum', 'min': 0 * keV, 'max': 5000 * keV}  # should be strictly equal to 'Singles'
    ]
    cc.output_filename = hc.output_filename
    print("ene win digit output path", cc.get_output_path())

    # projection
    for k, v in sim.volume_manager.volumes.items():
        if "crystal" in k:
            crystal = v
    # 2D binning projection
    proj = sim.add_actor("DigitizerProjectionActor", "Projection")
    proj.attached_to = crystal.name
    # we set two times the spectrum channel to compare with Gate output
    proj.input_digi_collections = ["Singles", "scatter", "peak140", "Singles"]
    proj.spacing = [4.41806 * mm, 4.41806 * mm]
    proj.size = [128, 128]
    # proj.plane = 'XY' # not implemented yet
    proj.output_filename = "proj028_colli.mhd"
    print("proj filename", proj.output_filename)
    print("proj output path", proj.get_output_path())

    # rotate spect
    cm = gate.g4_units.cm
    psd = 6.11 * cm
    p = [0, 0, -(15 * cm + psd)]
    spect.translation, spect.rotation = gate.geometry.utility.get_transform_orbiting(
        p, "y", 15
    )
    print("rotation 15 deg and translation = ", spect.translation)

    return spect, proj


def compare_result(sim, proj, fig_name, sum_tolerance=8):
    gate.exception.warning("Compare acceptance angle skipped particles")
    stats = sim.get_actor("Stats")

    reference_ratio = 691518 / 2998895  # (23%)
    b1 = gate.sources.generic.get_source_zero_events(sim, "beam1")
    b2 = gate.sources.generic.get_source_zero_events(sim, "beam2")
    b3 = gate.sources.generic.get_source_zero_events(sim, "beam3")
    print(f"Number of zeros events: {b1} {b2} {b3}")

    print(f"Number of simulated events: {stats.counts.events}")
    beam1 = sim.source_manager.get_source_info("beam1")
    mode = beam1.direction.acceptance_angle.skip_policy
    stats_ref = utility.read_stat_file(paths.gate_output / "stat4.txt")

    if mode == "SkipEvents":
        b1 = gate.sources.generic.get_source_skipped_events(sim, "beam1")
        b2 = gate.sources.generic.get_source_skipped_events(sim, "beam2")
        b3 = gate.sources.generic.get_source_skipped_events(sim, "beam3")
        stats.counts.events = stats.counts.events + b1 + b2 + b3
        print(f"Skip Events mode, adding the skipped ones")
        print(f"Number of simulated events: {stats.counts.events}")
        # do not compare track in this mode
        stats.counts.tracks = stats_ref.counts.tracks

    tol = 0.3
    r1 = b1 / stats.counts.events
    is_ok = (r1 - reference_ratio) / reference_ratio < tol
    utility.print_test(
        is_ok,
        f"Skipped particles b1 = {b1} {r1 * 100:.2f} %  vs {reference_ratio * 100:.2f} % ",
    )

    r2 = b2 / stats.counts.events
    is_ok = (r2 - reference_ratio) / reference_ratio < tol
    utility.print_test(
        is_ok,
        f"Skipped particles b2 = {b2} {r2 * 100:.2f} %  vs {reference_ratio * 100:.2f} % ",
    )

    r3 = b3 / stats.counts.events
    is_ok = (r3 - reference_ratio) / reference_ratio < tol
    utility.print_test(
        is_ok,
        f"Skipped particles b3 = {b3} {r3 * 100:.2f} %  vs {reference_ratio * 100:.2f} % ",
    )

    # stat
    gate.exception.warning("Compare stats")
    print(stats)
    print(f"Number of runs was {stats.counts.runs}. Set to 1 before comparison")
    stats.counts.runs = 1  # force to 1
    print(
        f"Number of steps was {stats.counts.steps}, force to the same value (because of angle acceptance). "
    )
    stats.counts.steps = stats_ref.counts.steps  # force to id
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
            tolerance=85,
            ignore_value=0,
            axis="x",
            sum_tolerance=sum_tolerance,
            fig_name=str(paths.output / fig_name),
        )
        and is_ok
    )

    return is_ok

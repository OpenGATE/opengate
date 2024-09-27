#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect.ge_discovery_nm670 as gate_spect
import opengate.contrib.phantoms.nemaiec as gate_iec
from scipy.spatial.transform import Rotation


def create_simulation(sim, aa_flag, paths):
    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.random_seed = 3456789
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    cm3 = gate.g4_units.cm3
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.second
    BqmL = Bq / cm3

    sim.user_hook_after_init = gate.userhooks.check_production_cuts

    # world size
    sim.world.size = [2 * m, 2 * m, 2 * m]
    sim.world.material = "G4_AIR"

    # spect head (no collimator)
    spect, colli, crystal = gate_spect.add_spect_head(
        sim, "spect", collimator_type=False, debug=False
    )

    # iec phantom
    gate_iec.add_iec_phantom(sim)

    # two sources (no background yet)
    activity_concentration = 5000 * BqmL / sim.number_of_threads
    ac = activity_concentration
    sources = gate_iec.add_spheres_sources(
        sim,
        "iec",
        "iec_source",
        [10, 13, 17, 22, 28, 37],
        [ac, ac, ac, ac, ac, ac],
        verbose=True,
    )

    for s in sources:
        s.particle = "gamma"
        s.energy.type = "mono"
        s.energy.mono = 140 * keV
        # WARNING : to speed up, this is not a iso source,
        # s.direction.type = "iso"
        s.direction.type = "momentum"
        s.direction.momentum = [0, 1, 0]
        s.direction.acceptance_angle.volumes = ["spect"]
        s.direction.acceptance_angle.intersection_flag = aa_flag
        s.direction.acceptance_angle.skip_policy = "ZeroEnergy"

    sources = gate_iec.add_spheres_sources(
        sim,
        "iec",
        "iec_source2",
        [10, 13, 17, 22, 28, 37],
        [ac, ac, ac, ac, ac, ac],
        verbose=True,
    )

    for s in sources:
        s.particle = "gamma"
        s.energy.type = "mono"
        s.energy.mono = 140 * keV
        # WARNING : to speed up, this is not an iso source,
        # s.direction.type = "iso"
        s.direction.type = "momentum"
        s.direction.momentum = [1, 0, 0]
        s.direction.acceptance_angle.volumes = ["spect"]
        s.direction.acceptance_angle.intersection_flag = aa_flag
        s.direction.acceptance_angle.skip_policy = "ZeroEnergy"

    # physic list
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

    # set cuts
    sim.physics_manager.set_production_cut(
        volume_name="world",
        particle_name="all",
        value=10 * mm,
    )

    sim.physics_manager.set_production_cut(
        volume_name="spect",
        particle_name="all",
        value=1 * mm,
    )

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.output_filename = "stats029.txt"

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.attached_to = "spect_crystal"
    hc.output_filename = "test029.root"
    if sim.number_of_threads == 1:
        hc.root_output.write_to_disk = False
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # singles collection
    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.attached_to = hc.attached_to
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.output_filename = hc.output_filename

    # EnergyWindows
    cc = sim.add_actor("DigitizerEnergyWindowsActor", "EnergyWindows")
    cc.attached_to = hc.attached_to
    cc.input_digi_collection = "Singles"
    cc.channels = [
        {"name": "scatter", "min": 114 * keV, "max": 126 * keV},
        {"name": "peak140", "min": 126 * keV, "max": 154.55 * keV},
    ]
    cc.output_filename = hc.output_filename

    # projections
    proj = sim.add_actor("DigitizerProjectionActor", "Projection")
    proj.attached_to = hc.attached_to
    proj.input_digi_collections = ["Singles", "scatter", "peak140"]
    proj.spacing = [4.41806 * mm, 4.41806 * mm]
    proj.size = [128, 128]
    proj.origin_as_image_center = False
    proj.output_filename = "proj029.mhd"

    translations = []
    rotations = []
    n = 9
    sim.run_timing_intervals = []
    gantry_rotation = -90
    start_t = 0
    end = 1 * sec / n
    initial_rot = Rotation.from_euler("X", 90, degrees=True)
    for r in range(n):
        t, rot = gate.geometry.utility.get_transform_orbiting(
            [0, 30 * cm, 0], "Z", gantry_rotation
        )
        rot = Rotation.from_matrix(rot)
        rot = rot * initial_rot
        rot = rot.as_matrix()
        translations.append(t)
        rotations.append(rot)
        sim.run_timing_intervals.append([start_t, end])
        gantry_rotation += 10
        start_t = end
        end += 1 * sec / n
    spect.add_dynamic_parametrisation(translation=translations, rotation=rotations)

    # Warning : we set the initial position for the spect
    # is it not really used (because the motion actor) but needed to test overlap
    spect.translation = translations[0]
    spect.rotation = rotations[0]

    print(f"Run {len(sim.run_timing_intervals)} intervals: {sim.run_timing_intervals}")

    # check actor priority: the MotionVolumeActor must be first
    l = [l for l in sim.actor_manager.user_info_actors.values()]
    sorted_actors = sorted(l, key=lambda d: d.priority)
    print(f"Actors order: ", [[l.name, l.priority] for l in sorted_actors])

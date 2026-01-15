#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test054")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.visu_type = "qt"
    # sim.visu = True
    sim.check_volumes_overlap = True
    sim.number_of_threads = 1
    sim.random_seed = 654923
    sim.output_dir = paths.output

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm
    sec = gate.g4_units.second

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_AIR"

    # image
    patient = sim.add_volume("Box", "patient")
    patient.material = "G4_WATER"
    patient.size = [200 * mm, 200 * mm, 200 * mm]
    patient.translation = [0, 0, 0]

    # create two other parallel worlds
    sim.add_parallel_world("world2")

    # detector in w2 (on top of world)
    det = sim.add_volume("Box", "detector")
    det.mother = "world2"
    det.material = "NaI"
    det.size = [400 * mm, 400 * mm, 40 * mm]
    det.translation = [0, 0, 100 * mm]

    n = 2
    interval_length = 1 * sec / n
    sim.run_timing_intervals = [
        (i * interval_length, (i + 1) * interval_length) for i in range(n)
    ]
    gantry_angles_deg = [[i * 20] for i in range(n)]
    (
        dynamic_translations,
        dynamic_rotations,
    ) = gate.geometry.utility.get_transform_orbiting(
        initial_position=det.translation, axis="Y", angle_deg=gantry_angles_deg
    )
    print(dynamic_translations)
    print(dynamic_rotations)
    print(sim.run_timing_intervals)

    det.add_dynamic_parametrisation(
        rotation=dynamic_rotations, translation=dynamic_translations
    )

    # source
    source = sim.add_source("GenericSource", "source")
    source.energy.mono = 0.144 * MeV
    source.particle = "gamma"
    source.position.type = "box"
    source.position.size = [1 * mm, 200 * mm, 1 * mm]
    source.position.translation = [0, 0, 0 * cm]
    source.activity = 1e5 * Bq / sim.number_of_threads
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.attached_to = det
    hc.attributes = [
        "KineticEnergy",
        "PostPosition",
        "PrePosition",
        "TotalEnergyDeposit",
        "GlobalTime",
        "TrackVolumeName",
        "TrackID",
        "PostStepUniqueVolumeID",
        "PreStepUniqueVolumeID",
        "TrackVolumeCopyNo",
        "TrackVolumeInstanceID",
        "TrackVertexKineticEnergy",
        "TrackVertexPosition",
        "ProcessDefinedStep",
        "EventPosition",
    ]
    hc.output_filename = "hits.root"

    cc = sim.add_actor("DigitizerEnergyWindowsActor", "EnergyWindows")
    keV = gate.g4_units.keV
    channels = [
        # {"name": f"spectrum_{detector}", "min": 3 * keV, "max": 515 * keV},
        {"name": f"scatter", "min": 108.57749938965 * keV, "max": 129.5924987793 * keV},
        {"name": f"peak140", "min": 129.5924987793 * keV, "max": 150.60751342773 * keV},
    ]
    cc.attached_to = hc.attached_to
    cc.input_digi_collection = hc.name
    cc.channels = channels
    cc.output_filename = hc.output_filename

    # projection
    proj = sim.add_actor("DigitizerProjectionActor", "Projection")
    proj.attached_to = cc.attached_to
    proj.input_digi_collections = [x["name"] for x in cc.channels]

    # Only record primary window
    proj.input_digi_collections = ["peak140"]
    proj.spacing = [2.46 * mm, 2.46 * mm]
    proj.size = [128, 16]
    proj.origin_as_image_center = True
    proj.output_filename = "projections.mha"

    # --------------------------------------------------------------------------
    print("Geometry trees: ")
    print(sim.volume_manager.dump_volume_tree())

    # start simulation
    sim.run()

    # print results at the end
    print(stats)

    # check image
    is_ok = utility.assert_images(
        paths.output_ref / "projections.mha",
        proj.get_output_path("counts"),
        stats=stats,
        tolerance=40,
        axis="x",
        sad_profile_tolerance=15,
        fig_name=sim.output_dir / "parallel_proj.png",
    )
    utility.test_ok(is_ok)

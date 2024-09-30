#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import pathlib


def user_hook_volume(simulation_engine):
    sphere_volume = simulation_engine.volume_engine.get_volume("mysphere")
    (
        global_translation_old,
        global_rotation_old,
    ) = gate.geometry.utility.get_transform_world_to_local_old(sphere_volume.name)
    (
        global_translation_new,
        global_rotation_new,
    ) = gate.geometry.utility.get_transform_world_to_local(sphere_volume)
    print("***********************************************************")
    print(f"World to local transform for volume {sphere_volume.name}: ")
    print("global_translation_old, global_rotation_old: ")
    print(global_translation_old, global_rotation_old)
    print("global_translation_new, global_rotation_new: ")
    print(global_translation_new, global_rotation_new)
    print("***********************************************************")


def check_mat(se):
    pathFile = pathlib.Path(__file__).parent.resolve()

    # explicit check overlap (already performed during initialize)
    print("check overlap with verbose")
    se.check_volumes_overlap(verbose=True)
    sim = se.simulation

    # print info material db
    dbn = sim.volume_manager.dump_material_database_names()
    mnist = se.volume_engine.get_database_material_names("NIST")
    mdb = se.volume_engine.get_database_material_names(
        pathFile.parent / "data" / "GateMaterials.db"
    )
    dm = se.volume_engine.dump_build_materials()
    print("Material info:")
    print("\t databases    :", dbn)
    print("\t mat in NIST  :", len(mnist), mnist)
    print("\t mat in db    :", mdb)
    print("\t defined mat  :", dm)

    print("dbn", dbn)
    assert dbn == [pathFile.parent / "data" / "GateMaterials.db"]
    # assert len(mnist) == 308  # Geant4 11.02
    assert len(mnist) == 309  # Geant4 11.1
    assert mdb == [
        "Vacuum",
        "Aluminium",
        "Uranium",
        "Silicon",
        "Germanium",
        "Yttrium",
        "Gadolinium",
        "Lutetium",
        "Tungsten",
        "Lead",
        "Bismuth",
        "NaI",
        "NaITl",
        "PWO",
        "BGO",
        "LSO",
        "Plexiglass",
        "GSO",
        "LuAP",
        "YAP",
        "Water",
        "Quartz",
        "Breast",
        "Air",
        "Glass",
        "Scinti-C9H10",
        "LuYAP-70",
        "LuYAP-80",
        "Plastic",
        "CZT",
        "Lung",
        "Polyethylene",
        "PVC",
        "SS304",
        "PTFE",
        "LYSO",
        "Body",
        "Muscle",
        "LungMoby",
        "SpineBone",
        "RibBone",
        "Adipose",
        "Blood",
        "Heart",
        "Kidney",
        "Liver",
        "Lymph",
        "Pancreas",
        "Intestine",
        "Skull",
        "Cartilage",
        "Brain",
        "Spleen",
        "Testis",
        "PMMA",
    ]
    assert dm == ["G4_AIR", "G4_WATER", "Lead", "Lung", "G4_LUCITE"]
    assert len(se.volume_engine.dump_build_materials()) == 5


if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()
    paths = utility.get_default_test_paths(__file__)

    # create the simulation
    sim = gate.Simulation()
    print(f"Volumes types: {sim.volume_manager.dump_volume_types()}")

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.store_json_archive = True
    sim.output_dir = paths.output / "test007"

    # add a material database
    sim.volume_manager.add_material_database(
        pathFile.parent / "data" / "GateMaterials.db"
    )

    #  change world size
    m = gate.g4_units.m
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]

    # add a simple volume
    waterbox = sim.add_volume("Box", "Waterbox")
    cm = gate.g4_units.cm
    waterbox.size = [60 * cm, 60 * cm, 60 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 35 * cm]
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]  # blue

    # another (child) volume with rotation
    mm = gate.g4_units.mm
    sheet = sim.add_volume("Box", "Sheet")
    sheet.size = [30 * cm, 30 * cm, 2 * mm]
    sheet.mother = "Waterbox"
    sheet.material = "Lead"
    r = Rotation.from_euler("x", 33, degrees=True)
    center = [0 * cm, 0 * cm, 10 * cm]
    t = gate.geometry.utility.get_translation_from_rotation_with_center(r, center)
    sheet.rotation = r.as_matrix()
    sheet.translation = t + [0 * cm, 0 * cm, -18 * cm]
    sheet.color = [1, 0, 0, 1]  # red

    # A sphere
    sph = sim.add_volume("Sphere", "mysphere")
    sph.rmax = 5 * cm
    sph.mother = "Waterbox"
    sph.translation = [0 * cm, 0 * cm, -8 * cm]
    sph.material = "Lung"
    sph.color = [0.5, 1, 0.5, 1]  # kind of green
    sph.toto = "nothing"  # ignored, should raise a warning

    # A ...thing ?
    trap = sim.add_volume("Trap", "mytrap")
    trap.mother = "Waterbox"
    trap.translation = [0, 0, 15 * cm]
    trap.material = "G4_LUCITE"

    # default source for tests
    source = sim.add_source("GenericSource", "Default")
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    source.particle = "proton"
    source.energy.mono = 240 * MeV
    source.position.radius = 1 * cm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 2500 * Bq

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    # run timing
    sec = gate.g4_units.second
    sim.run_timing_intervals = [
        [0, 0.5 * sec]
        # ,[0.5 * sec, 1.2 * sec]
    ]

    print(sim)

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")
    # sim.g4_com("/run/verbose 2")
    # sim.g4_com("/event/verbose 2")
    # sim.g4_com("/tracking/verbose 1")

    # start simulation
    sim.user_hook_after_init = check_mat
    sim.user_hook_after_run = user_hook_volume
    # should be sim.run(start_new_process=True)
    # but for testing, we currently set it to False
    sim.run(start_new_process=False)

    # print results at the end
    print(stats)

    # check
    stats_ref = gate.actors.miscactors.SimulationStatisticsActor(name="ref")
    c = stats_ref.counts
    c.runs = 1
    c.events = 1280
    c.tracks = 17034  # 25668
    c.steps = 78096  # 99465
    # stats_ref.pps = 506.6
    sec = gate.g4_units.second
    c.duration = 2.5267 * sec
    print("-" * 80)
    is_ok = utility.assert_stats(stats, stats_ref, 0.15)

    utility.test_ok(is_ok)

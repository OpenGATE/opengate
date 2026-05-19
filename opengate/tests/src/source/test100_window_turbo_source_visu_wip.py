#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import pathlib
import numpy as np
from box import Box
import matplotlib.pyplot as plt
from opengate.tests import utility

paths = utility.get_default_test_paths(__file__, output_folder="test100")


def build_collimator(sim, pin_radius_up=3.6, pin_radius_down=13.6):
    world = sim.world
    gcm3 = gate.g4_units.g_cm3
    mm = gate.g4_units.mm
    sim.volume_manager.material_database.add_material_weights(
        "Tungsten",
        ["W"],
        [1],
        19.3 * gcm3,
    )

    pinboard_inner = sim.add_volume("Box", "pinboard_inner")
    pinboard_inner.material = "Tungsten"
    pinboard_inner.translation = [0, 100 * mm, 0]
    pinboard_inner.size = [500 * mm, 2 * mm, 500 * mm]
    pinboard_inner.color = [0.5, 0.5, 0.5, 0.5]

    # kill_actor_inner = sim.add_actor("KillActor", "kill_inner")
    # kill_actor_inner.attached_to = "pinboard_inner"

    pinboard_cylinder = sim.add_volume("Tubs", "pin_cylinder")
    pinboard_cylinder.mother = pinboard_inner
    pinboard_cylinder.rmin = 0
    pinboard_cylinder.rmax = pin_radius_up * mm
    pinboard_cylinder.dz = 1 * mm
    pinboard_cylinder.material = "G4_AIR"
    pinboard_cylinder.rotation = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    pinboard_cylinder.color = [1, 1, 1, 1]

    pinboard_outer = sim.add_volume("Box", "pinboard_outer")
    pinboard_outer.mother = world
    pinboard_outer.material = "Tungsten"
    pinboard_outer.translation = [0, 92.49999 * mm, 0]
    pinboard_outer.size = [500 * mm, 13 * mm, 500 * mm]
    pinboard_outer.color = [0.5, 0.5, 0.5, 0.5]

    pin_cone = sim.add_volume("Cons", "pin_cone")
    pin_cone.mother = pinboard_outer
    pin_cone.rmax1 = pin_radius_up * mm
    pin_cone.rmax2 = pin_radius_down * mm
    pin_cone.rmin1 = 0
    pin_cone.rmin2 = 0
    pin_cone.dz = 6.5 * mm
    pin_cone.material = "G4_AIR"
    pin_cone.rotation = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    pin_cone.color = [1, 1, 1, 1]
    pin_cone.dphi = 2 * np.pi

    # kill_actor_outer = sim.add_actor("KillActor", "kill_outer")
    # kill_actor_outer.attached_to = "pinboard_outer"


def build_crystal(sim, prj_name):
    world = sim.world
    gcm3 = gate.g4_units.g_cm3
    sim.volume_manager.material_database.add_material_weights(
        "CsI",
        ["Cs", "I"],
        [1, 1],
        4.51 * gcm3,
    )

    mm = gate.g4_units.mm

    head_crystal = sim.add_volume("Box", "head_crystal")
    head_crystal.mother = world
    head_crystal.size = [160 * mm, 8 * mm, 160 * mm]
    head_crystal.material = "CsI"
    head_crystal.translation = [0, 229.4 * mm, 0]
    head_crystal.color = [0, 0, 1, 1]
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.attributes = [
        "TotalEnergyDeposit",
        "KineticEnergy",
        "PostPosition",
        "TrackCreatorProcess",
        "GlobalTime",
        "TrackVolumeName",
        "RunID",
        "ThreadID",
        "TrackID",
        "PreStepUniqueVolumeID",
    ]
    hc.attached_to = ["head_crystal"]
    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.group_volume = "head_crystal"
    proj = sim.add_actor("DigitizerProjectionActor", "Projection")
    proj.attached_to = "head_crystal"
    proj.input_digi_collections = ["Singles"]
    proj.spacing = [1.5 * mm, 1.5 * mm]
    proj.size = [100, 100]
    proj.origin_as_image_center = False
    proj.output_filename = f"{prj_name}.mhd"
    proj.detector_orientation_matrix = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])


def build_geometry(sim, prj_name, pin_radius_up=3.6, pin_radius_down=13.6):
    mm = gate.g4_units.mm
    world = sim.world
    world.size = [500 * mm, 500 * mm, 500 * mm]
    world.color = [1, 1, 1, 0.05]
    build_collimator(sim, pin_radius_up, pin_radius_down)
    build_crystal(sim, prj_name)


def change_source_parameters(source_back, source_1, source_2, source_3):
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    source_back.particle = "gamma"
    source_back.energy.mono = 141 * keV
    source_back.position.type = "cylinder"
    source_back.position.translation = [0, -100, 0]
    source_back.position.radius = 100 * mm
    source_back.position.dz = 100 * mm

    source_1.particle = "gamma"
    source_1.energy.mono = 141 * keV
    source_1.position.type = "cylinder"
    source_1.position.translation = [-50, -100, 0]
    source_1.position.radius = 10 * mm
    source_1.position.dz = 100 * mm

    source_2.particle = "gamma"
    source_2.energy.mono = 141 * keV
    source_2.position.type = "cylinder"
    source_2.position.translation = [0, -100, 0]
    source_2.position.radius = 15 * mm
    source_2.position.dz = 100 * mm

    source_3.particle = "gamma"
    source_3.energy.mono = 141 * keV
    source_3.position.type = "cylinder"
    source_3.position.translation = [50, -100, 0]
    source_3.position.radius = 20 * mm
    source_3.position.dz = 100 * mm


def initialize(duration=10):
    sim = gate.Simulation()
    sec = gate.g4_units.second
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1 * gate.g4_units.mm
    # main options
    sim.g4_verbose = True
    sim.g4_verbose_level = 1
    sim.visu = True
    sim.visu_type = "qt"
    sim.number_of_threads = 1
    sim.progress_bar = True
    sim.run_timing_intervals = [[0, duration * sec]]
    sim.add_actor("SimulationStatisticsActor", "Stats")
    return sim


def calculate_profile(image_path):
    import SimpleITK as sitk

    image = sitk.ReadImage(image_path)
    array = sitk.GetArrayFromImage(image)
    profile = np.sum(array, axis=(0, 1))
    return profile


def compare_profiles(ref, test, tolerance=8.0, fig_name=None):
    ref = np.asarray(ref, dtype=float)
    test = np.asarray(test, dtype=float)

    if ref.shape != test.shape:
        utility.print_test(False, f"Profile shapes differ: {ref.shape} vs {test.shape}")
        return False

    sad = np.abs(ref - test).sum() / (ref.sum() + test.sum()) * 100
    is_ok = sad < tolerance
    utility.print_test(
        is_ok, f"Profile relative SAD = {sad:.2f}% (tol {tolerance:.2f}%)"
    )

    if fig_name is not None:
        plt.figure(figsize=(10, 5))
        plt.plot(ref / ref.sum(), label="reference")
        plt.plot(test / test.sum(), label="test")
        plt.legend()
        plt.xlabel("Pixel")
        plt.ylabel("Normalized counts")
        plt.savefig(fig_name)

    return is_ok


def run_window_turbo_source(activity=1):
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm
    sim = initialize(0)
    sim.g4_verbose = True
    sim.number_of_threads = 2
    sim.random_seed = 1
    radius_down = 13.6
    build_geometry(sim, paths.output / "window_turbo", pin_radius_down=radius_down)
    source_back = sim.add_source("WindowTurboSource", "source_back")
    source_1 = sim.add_source("WindowTurboSource", "source_1")
    source_2 = sim.add_source("WindowTurboSource", "source_2")
    source_3 = sim.add_source("WindowTurboSource", "source_3")
    source_1.activity = activity * Bq
    source_2.activity = activity * Bq
    source_3.activity = activity * Bq
    source_back.activity = activity * Bq
    source_back.direction.a1 = -radius_down * mm
    source_back.direction.a2 = radius_down * mm
    source_back.direction.b1 = -radius_down * mm
    source_back.direction.b2 = radius_down * mm
    source_back.direction.plane_distance = 99 * mm
    source_back.direction.plane_phi = np.pi / 2
    source_2.direction = source_back.direction.copy()
    source_3.direction = source_back.direction.copy()
    source_1.direction = source_back.direction.copy()
    change_source_parameters(source_back, source_1, source_2, source_3)
    source_back.visualize_window("red", 2, 0)
    sim.run()
    stats = sim.get_actor("Stats")
    print(stats)
    print("-" * 80)


def run_generic_source(activity=1000000):
    Bq = gate.g4_units.Bq

    sim = initialize()
    build_geometry(sim, "generic")

    # physic list
    # print('Phys lists :', sim.get_available_physicLists())

    source_back = sim.add_source("GenericSource", "source_back")
    source_1 = sim.add_source("GenericSource", "source_1")
    source_2 = sim.add_source("GenericSource", "source_2")
    source_3 = sim.add_source("GenericSource", "source_3")
    source_1.activity = activity * Bq
    source_2.activity = activity * Bq
    source_3.activity = activity * Bq
    source_back.activity = activity * Bq
    change_source_parameters(source_back, source_1, source_2, source_3)

    sim.run()

    stats = sim.get_actor("Stats")
    print(stats)
    print("-" * 80)


if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()
    # run_generic_source()
    run_window_turbo_source()
    # profile_wt = calculate_profile(paths.output / "window_turbo_counts.mhd")
    # profile_generic = calculate_profile(paths.output_ref / "generic.mhd")
    # compare_result = compare_profiles(
    #     profile_generic,
    #     profile_wt,
    #     tolerance=4.0,
    #     fig_name=paths.output / "profile_comparison.png",
    # )

    # utility.test_ok(compare_result)

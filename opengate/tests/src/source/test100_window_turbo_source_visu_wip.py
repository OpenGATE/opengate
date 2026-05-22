#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import pathlib
import numpy as np
from box import Box
import matplotlib.pyplot as plt
from opengate.tests import utility
from test100_window_turbo_source_base import build_geometry

paths = utility.get_default_test_paths(__file__, output_folder="test100")


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
    sim.number_of_threads = 1
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
    source_back.direction.plane_distance = 86 * mm
    source_back.direction.plane_phi = np.pi / 2
    source_2.direction = source_back.direction.copy()
    source_3.direction = source_back.direction.copy()
    source_1.direction = source_back.direction.copy()
    change_source_parameters(source_back, source_1, source_2, source_3)
    source_back.visualize_window("red", 2, 0)
    source_back.visualize(1000, "red", 2)
    source_1.visualize(1000, "green", 2)
    source_2.visualize(1000, "blue", 2)
    source_3.visualize(1000, "cyan", 2)
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

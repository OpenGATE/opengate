#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import pathlib
import numpy as np
from box import Box
import matplotlib.pyplot as plt
from opengate.tests import utility
import SimpleITK as sitk
from test100_window_turbo_source_base import build_geometry

paths = utility.get_default_test_paths(__file__, output_folder="test100")


def change_source_parameters(source_back):
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    source_back.particle = "gamma"
    source_back.energy.mono = 141 * keV
    source_back.position.type = "cylinder"
    source_back.position.translation = [0, -100, 0]
    source_back.position.radius = 100 * mm
    source_back.position.dz = 100 * mm


def make_itk_source():
    data = np.ones((13, 2))
    data[:, 1] = 0
    data = data.flatten()[:-1].reshape((5, 1, 5))
    itk_image = sitk.GetImageFromArray(data)
    itk_image.SetSpacing([50, 50, 50])
    itk_image.SetOrigin([-125 + 25, -125 + 25, -125 + 25])
    sitk.WriteImage(itk_image, paths.output / "voxel_source.mhd")
    print(data)


def initialize(duration=10):
    sim = gate.Simulation()
    sec = gate.g4_units.second
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1 * gate.g4_units.mm
    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.visu_type = "qt"
    sim.number_of_threads = 32
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


def run_window_turbo_source(activity=1000000):
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm
    sim = initialize(80)
    sim.g4_verbose = False
    sim.number_of_threads = 4
    sim.random_seed = 1
    radius_down = 13.6
    head_y_pos = 100
    build_geometry(
        sim,
        paths.output / "voxel_wt",
        pin_radius_down=radius_down,
        head_y_pos=head_y_pos,
    )
    voxel_wt_source = sim.add_source("VoxelWTSource", "source_back")
    voxel_wt_source.image = str(paths.output / "voxel_source.mhd")
    voxel_wt_source.activity = activity * Bq
    voxel_wt_source.direction.a1 = -radius_down * mm
    voxel_wt_source.direction.a2 = radius_down * mm
    voxel_wt_source.direction.b1 = -radius_down * mm
    voxel_wt_source.direction.b2 = radius_down * mm
    voxel_wt_source.direction.plane_distance = (head_y_pos - 14) * mm
    voxel_wt_source.direction.plane_phi = np.pi / 2
    # voxel_wt_source.visualize(2000,"red",5)
    # voxel_wt_source.visualize_window("red",2)
    change_source_parameters(voxel_wt_source)
    sim.run()
    stats = sim.get_actor("Stats")
    print(stats)
    print("-" * 80)


def run_generic_source(activity=1000000):
    Bq = gate.g4_units.Bq

    sim = initialize(10)
    sim.number_of_threads = 32
    build_geometry(sim, "voxel")

    # physic list
    # print('Phys lists :', sim.get_available_physicLists())

    voxel_source = sim.add_source("VoxelSource", "source_back")
    voxel_source.image = str(paths.output / "voxel_source.mhd")
    voxel_source.activity = activity * Bq
    change_source_parameters(voxel_source)
    # voxel_source.visualize(2000,"red",5)

    sim.run()

    stats = sim.get_actor("Stats")
    print(stats)
    print("-" * 80)


if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()
    make_itk_source()
    # run_generic_source(100)
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

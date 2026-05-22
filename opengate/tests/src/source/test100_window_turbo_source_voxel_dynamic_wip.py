#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import SimpleITK as sitk

import opengate as gate
from opengate.tests import utility
from test100_window_turbo_source_base import (
    build_geometry,
    calculate_profile,
    compare_profiles,
)

paths = utility.get_default_test_paths(__file__, output_folder="test100")


def make_itk_source(output_path, zero_first_voxel=False):
    data = np.ones((13, 2))
    data[:, 1] = 0
    data = data.flatten()[:-1].reshape((5, 1, 5))
    if zero_first_voxel:
        data.flat[0] = 0
    itk_image = sitk.GetImageFromArray(data)
    itk_image.SetSpacing([50, 50, 50])
    itk_image.SetOrigin([-125 + 25, -125 + 25, -125 + 25])
    sitk.WriteImage(itk_image, output_path)
    return output_path


def initialize(run_timing_intervals):
    sim = gate.Simulation()
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1 * gate.g4_units.mm
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.visu_type = "qt"
    sim.number_of_threads = 4
    sim.progress_bar = False
    sim.run_timing_intervals = run_timing_intervals
    sim.add_actor("SimulationStatisticsActor", "Stats")
    return sim


def change_source_parameters(source):
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    source.particle = "gamma"
    source.energy.mono = 141 * keV
    source.position.type = "cylinder"
    source.position.translation = [0, -100, 0]
    source.position.radius = 100 * mm
    source.position.dz = 100 * mm


def configure_voxel_wt_source(sim, image_path, activity=1000000):
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm
    radius_down = 13.6
    head_y_pos = 100

    voxel_wt_source = sim.add_source("VoxelWTSource", "source_back")
    voxel_wt_source.image = str(image_path)
    voxel_wt_source.activity = activity * Bq
    voxel_wt_source.direction.a1 = -radius_down * mm
    voxel_wt_source.direction.a2 = radius_down * mm
    voxel_wt_source.direction.b1 = -radius_down * mm
    voxel_wt_source.direction.b2 = radius_down * mm
    voxel_wt_source.direction.plane_distance = (head_y_pos - 14) * mm
    voxel_wt_source.direction.plane_phi = np.pi / 2
    change_source_parameters(voxel_wt_source)
    return voxel_wt_source


def projection_exists(image_path):
    if not image_path.exists():
        return False
    try:
        sitk.ReadImage(image_path)
    except RuntimeError:
        return False
    return True


def run_static_voxel_wt_source(image_path, output_name):
    output_path = paths.output / f"{output_name}_counts.mhd"
    if projection_exists(output_path):
        print(f"Reuse existing static projection: {output_path}")
        return output_path

    sec = gate.g4_units.second
    interval_duration = 1920 // 4
    sim = initialize([[0, interval_duration * sec]])
    build_geometry(
        sim,
        paths.output / output_name,
        pin_radius_down=13.6,
        head_y_pos=100,
    )
    configure_voxel_wt_source(sim, image_path)
    sim.run(start_new_process=True)
    stats = sim.get_actor("Stats")
    print(stats)
    print("-" * 80)
    return output_path


def run_dynamic_voxel_wt_source(image_paths, output_name):
    sec = gate.g4_units.second
    interval_duration = 1920 // 4
    sim = initialize(
        [
            [0, interval_duration * sec],
            [interval_duration * sec, 2 * interval_duration * sec],
        ]
    )
    build_geometry(
        sim,
        paths.output / output_name,
        pin_radius_down=13.6,
        head_y_pos=100,
    )
    voxel_wt_source = configure_voxel_wt_source(sim, image_paths[0])
    voxel_wt_source.add_dynamic_parametrisation(image=image_paths)
    sim.run(start_new_process=True)
    stats = sim.get_actor("Stats")
    print(stats)
    print("-" * 80)

    expected_runs = sim.number_of_threads * len(sim.run_timing_intervals)
    stats_ok = stats.counts.runs == expected_runs
    utility.print_test(
        stats_ok,
        f"Stats runs count {stats.counts.runs} matches threads x timing intervals {expected_runs}",
    )
    return paths.output / f"{output_name}_counts.mhd", stats_ok


def calculate_dynamic_profiles(image_path):
    image = sitk.ReadImage(image_path)
    array = sitk.GetArrayFromImage(image)
    shape_ok = array.shape == (2, 100, 100)
    utility.print_test(
        shape_ok,
        f"Dynamic projection shape is {array.shape}, expected (2, 100, 100)",
    )
    if not shape_ok:
        return [], False
    return [np.sum(array[i], axis=0) for i in range(array.shape[0])], True


if __name__ == "__main__":
    source_image_0 = make_itk_source(paths.output / "voxel_source_dynamic_0.mhd")
    source_image_1 = make_itk_source(
        paths.output / "voxel_source_dynamic_1.mhd",
        zero_first_voxel=True,
    )

    static_projection_0 = run_static_voxel_wt_source(
        source_image_0,
        "voxel_wt_dynamic_static_0",
    )
    static_projection_1 = run_static_voxel_wt_source(
        source_image_1,
        "voxel_wt_dynamic_static_1",
    )
    dynamic_projection, stats_ok = run_dynamic_voxel_wt_source(
        [source_image_0, source_image_1],
        "voxel_wt_dynamic",
    )

    static_profile_0 = calculate_profile(static_projection_0)
    static_profile_1 = calculate_profile(static_projection_1)
    dynamic_profiles, shape_ok = calculate_dynamic_profiles(dynamic_projection)

    compare_result_0 = shape_ok and compare_profiles(
        static_profile_0,
        dynamic_profiles[0],
        tolerance=4.0,
        fig_name=paths.output / "profile_comparison_voxel_dynamic_0.png",
    )
    compare_result_1 = shape_ok and compare_profiles(
        static_profile_1,
        dynamic_profiles[1],
        tolerance=4.0,
        fig_name=paths.output / "profile_comparison_voxel_dynamic_1.png",
    )

    utility.test_ok(stats_ok and shape_ok and compare_result_0 and compare_result_1)

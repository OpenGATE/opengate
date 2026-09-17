#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import pathlib
import numpy as np
from box import Box
import matplotlib.pyplot as plt
import SimpleITK as sitk
from test100_window_turbo_source_base import (
    build_geometry,
    compare_profiles,
    calculate_profile,
)

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
    # print(data)


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


def run_window_turbo_source(activity=1000000):
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm
    NoT = 4
    sim = initialize(1920 // NoT)
    sim.g4_verbose = False

    sim.progress_bar = False
    sim.number_of_threads = NoT
    # sim.random_seed = 1
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
    total_num = 1920
    thread_count = 10
    duration = 1920 // thread_count
    sim = initialize(duration)
    sim.number_of_threads = thread_count
    build_geometry(sim, paths.output / f"voxel")

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
    # run_generic_source(1000000)
    run_window_turbo_source()
    profile_voxel_wt = calculate_profile(paths.output / "voxel_wt_counts.mhd")
    profile_voxel = calculate_profile(paths.output_ref / "voxel.mhd")
    compare_result = compare_profiles(
        profile_voxel,
        profile_voxel_wt,
        tolerance=4.0,
        fig_name=paths.output / "profile_comparison_voxel.png",
    )

    utility.test_ok(compare_result)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from opengate.image import *
import opengate.contrib.spect.siemens_intevo as intevo
from opengate.contrib.spect.spect_config import SPECTConfig
import opengate as gate


def create_test_spect_config(paths):
    data_path = paths.data
    mm = gate.g4_units.mm

    sc = SPECTConfig()
    sc.simu_name = "test090"
    sc.output_folder = paths.output
    # detectors
    sc.detector_config.model = "intevo"
    sc.detector_config.collimator = "melp"
    sc.detector_config.number_of_heads = 2
    sc.detector_config.digitizer_function = intevo.add_digitizer
    sc.detector_config.size = [256 / 4, 256 / 4]
    sc.detector_config.spacing = [2.39759994 * mm * 4, 2.39759994 * mm * 4]
    # phantom
    sc.phantom_config.image = data_path / "iec_5mm.mhd"
    sc.phantom_config.labels = data_path / "iec_5mm_labels.json"
    sc.phantom_config.material_db = data_path / "iec_5mm.db"
    # source
    sc.source_config.image = data_path / "iec_5mm_activity.mhd"
    sc.source_config.radionuclide = "177lu"
    sc.source_config.total_activity = 1e3 * gate.g4_units.Bq
    # acquisition
    sc.acquisition_config.radius = 350 * gate.g4_units.mm
    sc.acquisition_config.duration = 30 * gate.g4_units.s
    sc.acquisition_config.number_of_angles = 3
    return sc


def check_stats_file(n, sc, stats, is_ok, threads=1):
    print(stats.get_output_path())
    stats = utility.read_stats_file(stats.get_output_path())
    stats.counts.runs = int(stats.counts.runs / threads)
    print(stats)
    b = stats.counts.runs == sc.acquisition_config.number_of_angles
    is_ok = is_ok and b
    utility.print_test(
        b,
        f"Number of runs {sc.acquisition_config.number_of_angles} vs {stats.counts.runs}",
    )
    b = n * 0.9 < stats.counts.events < n * 1.1
    is_ok = is_ok and b
    utility.print_test(b, f"Number of events {n} vs {stats.counts.events}")
    return is_ok


def check_projection_files(
    sim,
    paths,
    stats,
    is_ok,
    tol=60,
    squared_flag=False,
    output_ref=None,
    scaling=1,
    axis="z",
    threads=1,
):
    stats = utility.read_stats_file(stats.get_output_path())
    stats.counts.runs = stats.counts.runs / threads
    if output_ref is None:
        output_ref = paths.output_ref
    # check images
    channel = sim.actor_manager.find_actors("energy_window")[0]
    projs = sim.actor_manager.find_actors("projection")
    for d in projs:
        # counts
        ref_file = output_ref / "projection_0_counts.mhd"
        img_file = d.get_output_path("counts")
        b = utility.assert_images(
            ref_file,
            img_file,
            tolerance=1000,
            ignore_value_data1=0,
            ignore_value_data2=0,
            sum_tolerance=tol,
            scaleImageValuesFactor=scaling,
            axis=axis,
        )
        is_ok = is_ok and b

        info = read_image_info(img_file)
        print(info.size, info.spacing)
        b = info.size[2] == len(channel.channels) * stats.counts.runs
        utility.print_test(
            b, f"Number of channels {len(channel.channels)}x{stats.counts.runs}"
        )
        is_ok = is_ok and b

        # squared
        if squared_flag:
            img_file = d.get_output_path("squared_counts")
            info = read_image_info(img_file)
            print(info.size, info.spacing)
            b = info.size[2] == len(channel.channels) * stats.counts.runs
            utility.print_test(
                b, f"Number of channels {len(channel.channels)}x{stats.counts.runs}"
            )
            is_ok = is_ok and b

    return is_ok

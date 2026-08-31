#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import Counter

import itk
import matplotlib.pyplot as plt
import numpy as np

import opengate as gate
from opengate.actors.dynamicactors import SourceActivityImageChanger
from opengate.tests import utility


def xyz_to_zyx(index_xyz):
    return tuple(reversed(index_xyz))


def create_activity_image(reference_image, peak_weights, output_path):
    array = np.zeros_like(itk.array_view_from_image(reference_image), dtype=np.float32)
    for peak_index_xyz, weight in peak_weights.items():
        array[xyz_to_zyx(peak_index_xyz)] = weight
    image = itk.image_from_array(array)
    image.CopyInformation(reference_image)
    itk.imwrite(image, str(output_path))
    return image


def create_reference_image(output_path):
    array = np.zeros((10, 10, 10), dtype=np.float32)
    image = itk.image_from_array(array)
    image.SetSpacing([1.0, 1.0, 1.0])
    image.SetOrigin([0.0, 0.0, 0.0])
    itk.imwrite(image, str(output_path))
    return image


def world_positions_to_voxel_indices(positions_xyz, image_info, source_translation):
    source_origin = (
        -image_info.size / 2.0 * image_info.spacing
        + np.array(source_translation, dtype=float)
        + image_info.spacing / 2.0
    )
    indices = np.floor((positions_xyz - source_origin) / image_info.spacing + 0.5)
    return indices.astype(int)


def count_indices(indices_xyz):
    return Counter(map(tuple, indices_xyz))


def plot_event_positions_and_decay(
    run_0_positions_xyz,
    run_1_positions_xyz,
    run_0_decay_times_sec,
    run_1_decay_times_sec,
    fit_x_0,
    fit_y_0,
    fit_x_1,
    fit_y_1,
    output_path,
):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), constrained_layout=True)

    axes[0].scatter(run_0_positions_xyz[:, 0], run_0_positions_xyz[:, 1], s=2)
    axes[0].set_title("Run 0 event positions")
    axes[0].set_xlabel("x [mm]")
    axes[0].set_ylabel("y [mm]")
    axes[0].set_aspect("equal", adjustable="box")

    axes[1].scatter(run_1_positions_xyz[:, 0], run_1_positions_xyz[:, 1], s=2)
    axes[1].set_title("Run 1 event positions")
    axes[1].set_xlabel("x [mm]")
    axes[1].set_ylabel("y [mm]")
    axes[1].set_aspect("equal", adjustable="box")

    axes[2].hist(
        run_0_decay_times_sec, bins="auto", density=True, alpha=0.6, label="run 0"
    )
    axes[2].hist(
        run_1_decay_times_sec, bins="auto", density=True, alpha=0.6, label="run 1"
    )
    axes[2].plot(fit_x_0, fit_y_0, label="fit run 0")
    axes[2].plot(fit_x_1, fit_y_1, label="fit run 1")
    axes[2].set_title("Event times by run")
    axes[2].set_xlabel("time [s]")
    axes[2].set_ylabel("density")
    axes[2].legend()

    fig.savefig(output_path)
    plt.close(fig)


def plot_decay_fit(
    all_event_times_sec,
    all_bin_edges,
    fit_x_0,
    fit_y_0,
    fit_x_1,
    fit_y_1,
    nominal_x,
    nominal_y,
    output_path,
):
    fig, ax = plt.subplots(1, 1, figsize=(9, 4), constrained_layout=True)
    ax.hist(all_event_times_sec, bins=all_bin_edges, alpha=0.7, label="events")
    ax.plot(fit_x_0, fit_y_0, label="fit run 0", linewidth=2)
    ax.plot(fit_x_1, fit_y_1, label="fit run 1", linewidth=2)
    ax.plot(nominal_x, nominal_y, label="nominal decay", linewidth=2, linestyle="--")
    ax.set_title("Event times with run-wise fits and nominal decay")
    ax.set_xlabel("time [s]")
    ax.set_ylabel("counts")
    ax.legend()
    fig.savefig(output_path)
    plt.close(fig)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test097")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 123456
    sim.output_dir = paths.output

    m = gate.g4_units.m
    mm = gate.g4_units.mm
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s

    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")
    sim.world.size = [1 * m, 1 * m, 1 * m]

    ct_image_path = paths.output / "ct_image.mhd"
    ct_itk = create_reference_image(ct_image_path)

    ct = sim.add_volume("Image", "ct")
    ct.image = str(ct_image_path)
    ct.material = "G4_AIR"
    ct.voxel_materials = [[0, 10, "G4_WATER"]]
    ct.load_input_image()

    source_image_1_path = paths.output / "dynamic_source_1.mhd"
    source_image_2_path = paths.output / "dynamic_source_2.mhd"
    run_0_primary_peak_xyz = (2, 5, 5)
    run_0_secondary_peak_xyz = (2, 2, 5)
    run_1_primary_peak_xyz = (7, 5, 5)
    run_1_secondary_peak_xyz = (7, 2, 5)
    run_0_expected_ratio = 3.0
    run_1_expected_ratio = 4.0
    create_activity_image(
        ct_itk,
        {
            run_0_primary_peak_xyz: run_0_expected_ratio,
            run_0_secondary_peak_xyz: 1.0,
        },
        source_image_1_path,
    )
    create_activity_image(
        ct_itk,
        {
            run_1_primary_peak_xyz: run_1_expected_ratio,
            run_1_secondary_peak_xyz: 1.0,
        },
        source_image_2_path,
    )
    source_info = gate.image.read_image_info(str(source_image_1_path))

    source = sim.add_source("VoxelSource", "vox_source")
    source.attached_to = ct.name
    source.particle = "gamma"
    source.activity = 50000 * Bq
    source.half_life = 2 * sec
    source.image = str(source_image_1_path)
    source.direction.type = "iso"
    source.position.translation = gate.image.get_translation_between_images_center(
        ct.image, source_image_1_path
    )
    source.energy.mono = 140 * keV
    source.add_dynamic_parametrisation(image=[source_image_1_path, source_image_2_path])

    # Explicit manual changer creation is only used here to test the changer API.
    # Normal user scripts should rely on add_dynamic_parametrisation(...), which
    # auto-creates the SourceActivityImageChanger.
    changer = SourceActivityImageChanger(
        name="source_activity_image_changer",
        activity_images=[source_image_1_path, source_image_2_path],
        attached_to=source,
        simulation=sim,
    )

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attributes = ["EventPosition", "GlobalTime", "RunID"]
    phsp.steps_to_store = "first"
    phsp.output_filename = "test097_dynamic_voxel_source_half_life.root"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.all = 1 * mm
    sim.run_timing_intervals = [(0, 2.5 * sec), (3.0 * sec, 5.5 * sec)]

    sim.run()

    root_data, _ = utility.open_root_as_np(phsp.get_output_path(), "phsp")
    event_times_sec = root_data["GlobalTime"] / sec
    run_ids = root_data["RunID"]
    event_positions_xyz = np.column_stack(
        (
            root_data["EventPosition_X"],
            root_data["EventPosition_Y"],
            root_data["EventPosition_Z"],
        )
    )
    event_indices_xyz = world_positions_to_voxel_indices(
        event_positions_xyz, source_info, source.position.translation
    )

    run_0_mask = run_ids == 0
    run_1_mask = run_ids == 1
    run_0_indices = event_indices_xyz[run_0_mask]
    run_1_indices = event_indices_xyz[run_1_mask]
    run_0_positions = event_positions_xyz[run_0_mask]
    run_1_positions = event_positions_xyz[run_1_mask]
    run_0_event_times_sec = event_times_sec[run_0_mask]
    run_1_event_times_sec = event_times_sec[run_1_mask]
    run_0_counts = count_indices(run_0_indices)
    run_1_counts = count_indices(run_1_indices)

    run_0_primary_counts = run_0_counts[run_0_primary_peak_xyz]
    run_0_secondary_counts = run_0_counts[run_0_secondary_peak_xyz]
    run_1_primary_counts = run_1_counts[run_1_primary_peak_xyz]
    run_1_secondary_counts = run_1_counts[run_1_secondary_peak_xyz]
    run_0_other_primary_counts = run_0_counts[run_1_primary_peak_xyz]
    run_1_other_primary_counts = run_1_counts[run_0_primary_peak_xyz]

    run_0_ratio = run_0_primary_counts / run_0_secondary_counts
    run_1_ratio = run_1_primary_counts / run_1_secondary_counts
    ratio_tolerance = 0.7

    fitted_half_life_run_0_sec, fit_x_0, fit_y_0_density = (
        utility.fit_exponential_decay(run_0_event_times_sec, 0.0, 2.5)
    )
    fitted_half_life_run_1_sec, fit_x_1, fit_y_1_density = (
        utility.fit_exponential_decay(run_1_event_times_sec, 3.0, 5.5)
    )
    expected_half_life_sec = source.half_life / sec
    half_life_run_0_relative_error = (
        abs(fitted_half_life_run_0_sec - expected_half_life_sec)
        / expected_half_life_sec
    )
    half_life_run_1_relative_error = (
        abs(fitted_half_life_run_1_sec - expected_half_life_sec)
        / expected_half_life_sec
    )
    half_life_difference_relative_error = (
        abs(fitted_half_life_run_0_sec - fitted_half_life_run_1_sec)
        / expected_half_life_sec
    )
    half_life_tolerance = 0.10

    combined_counts, combined_bin_edges = np.histogram(event_times_sec, bins="auto")
    combined_bin_width = np.mean(np.diff(combined_bin_edges))
    fit_y_0 = fit_y_0_density * len(run_0_event_times_sec) * combined_bin_width
    fit_y_1 = fit_y_1_density * len(run_1_event_times_sec) * combined_bin_width

    nominal_x = np.linspace(0.0, 5.5, 300)
    nominal_decay_constant = np.log(2.0) / expected_half_life_sec
    nominal_y = (
        source.activity
        / Bq
        * np.exp(-nominal_decay_constant * nominal_x)
        * combined_bin_width
    )

    plot_event_positions_and_decay(
        run_0_positions,
        run_1_positions,
        run_0_event_times_sec,
        run_1_event_times_sec,
        fit_x_0,
        fit_y_0_density,
        fit_x_1,
        fit_y_1_density,
        paths.output / "test097_dynamic_voxel_source_half_life.png",
    )
    plot_decay_fit(
        event_times_sec,
        combined_bin_edges,
        fit_x_0,
        fit_y_0,
        fit_x_1,
        fit_y_1,
        nominal_x,
        nominal_y,
        paths.output / "test097_dynamic_voxel_source_half_life_decay.png",
    )

    is_ok = True
    utility.print_test(
        changer.attached_to == source.name,
        f"Changer attached_to property resolves to source name: {changer.attached_to}",
    )
    is_ok = changer.attached_to == source.name and is_ok

    utility.print_test(
        stats.counts.runs == len(sim.run_timing_intervals),
        f"Stats runs count {stats.counts.runs} matches number of timing intervals",
    )
    is_ok = stats.counts.runs == len(sim.run_timing_intervals) and is_ok

    utility.print_test(
        run_0_other_primary_counts == 0,
        f"Run 0 contains no events in inactive run 1 primary voxel: {run_0_other_primary_counts}",
    )
    is_ok = run_0_other_primary_counts == 0 and is_ok

    utility.print_test(
        run_1_other_primary_counts == 0,
        f"Run 1 contains no events in inactive run 0 primary voxel: {run_1_other_primary_counts}",
    )
    is_ok = run_1_other_primary_counts == 0 and is_ok

    utility.print_test(
        abs(run_0_ratio - run_0_expected_ratio) < ratio_tolerance,
        f"Run 0 event-count ratio at xyz {run_0_primary_peak_xyz}/{run_0_secondary_peak_xyz}: {run_0_ratio:.2f}, expected {run_0_expected_ratio:.2f}",
    )
    is_ok = abs(run_0_ratio - run_0_expected_ratio) < ratio_tolerance and is_ok

    utility.print_test(
        abs(run_1_ratio - run_1_expected_ratio) < ratio_tolerance,
        f"Run 1 event-count ratio at xyz {run_1_primary_peak_xyz}/{run_1_secondary_peak_xyz}: {run_1_ratio:.2f}, expected {run_1_expected_ratio:.2f}",
    )
    is_ok = abs(run_1_ratio - run_1_expected_ratio) < ratio_tolerance and is_ok

    utility.print_test(
        half_life_run_0_relative_error < half_life_tolerance,
        f"Run 0 half life {expected_half_life_sec:.2f} sec vs fitted {fitted_half_life_run_0_sec:.2f} sec",
    )
    is_ok = half_life_run_0_relative_error < half_life_tolerance and is_ok

    utility.print_test(
        half_life_run_1_relative_error < half_life_tolerance,
        f"Run 1 half life {expected_half_life_sec:.2f} sec vs fitted {fitted_half_life_run_1_sec:.2f} sec",
    )
    is_ok = half_life_run_1_relative_error < half_life_tolerance and is_ok

    utility.print_test(
        half_life_difference_relative_error < half_life_tolerance,
        f"Run 0/1 fitted half lives agree: {fitted_half_life_run_0_sec:.2f} sec vs {fitted_half_life_run_1_sec:.2f} sec",
    )
    is_ok = half_life_difference_relative_error < half_life_tolerance and is_ok

    utility.test_ok(is_ok)

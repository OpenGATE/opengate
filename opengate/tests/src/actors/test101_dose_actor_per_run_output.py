#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

import itk
import numpy as np

import opengate as gate
from opengate.tests import utility


def get_single_voxel_value_from_image(image):
    return float(np.asarray(itk.GetArrayViewFromImage(image)).ravel()[0])


def read_single_voxel_value(path):
    return get_single_voxel_value_from_image(itk.imread(str(path)))


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder=Path(__file__).stem)

    # This test exercises actor-output consistency over multiple runs in a
    # simple setup without job splitting:
    # - keep per-run dose output on disk and in memory
    # - keep the merged dose output
    # - verify that per-run outputs scale with the requested number of
    #   primaries and that their sum matches the merged output
    # - verify analogous per-run and merged consistency for the statistics actor
    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 123456789
    sim.output_dir = paths.output

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    sec = gate.g4_units.s
    nm = gate.g4_units.nm

    sim.world.size = [1 * m, 1 * m, 1 * m]

    # Use one homogeneous water box so the setup stays minimal and essentially
    # all scored dose comes from one simple target volume.
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [20 * cm, 20 * cm, 20 * cm]
    waterbox.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    sim.physics_manager.enable_decay = False

    # Use a low-energy proton source fully contained in the water box. The
    # source is configured with a distinct number of primaries per run so the
    # dose output should scale accordingly.
    source = sim.add_source("GenericSource", "source")
    source.particle = "proton"
    source.energy.mono = 20 * MeV
    source.number_of_primaries = [1000, 3000, 5000]
    source.position.type = "disc"
    source.position.radius = 1 * nm
    source.position.translation = [0, 0, -9 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    # Score dose in a fake 3D image with a single voxel covering the whole box.
    # This makes the output comparison simple: each run and the merged result
    # reduce to one scalar voxel value while still exercising the normal image
    # output machinery.
    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = "waterbox"
    dose.size = [1, 1, 1]
    dose.spacing = [20 * cm, 20 * cm, 20 * cm]
    dose.translation = [0, 0, 0]
    dose.dose.active = True
    dose.dose.keep_data_per_run = True
    dose.dose.output_filename = "dose.mhd"

    # The statistics actor provides an independent consistency check on the
    # event accounting. Keep per-run data so we can verify run-by-run counts
    # against the expected primaries as well as merged consistency.
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "stats.txt"
    stats.keep_data_per_run = True

    sim.run_timing_intervals = [
        [0 * sec, 1 * sec],
        [1 * sec, 2 * sec],
        [2 * sec, 3 * sec],
    ]

    sim.run()

    expected_primaries = [1000, 3000, 5000]

    dose_values_from_memory = []
    dose_values_from_disk = []
    is_ok = True

    for run_index, n_primaries in enumerate(expected_primaries):
        run_image_memory = dose.dose.get_data(which=run_index)
        run_image_path = dose.dose.get_output_path(which=run_index)

        b = run_image_path.is_file()
        is_ok = utility.print_test(b, f"Run {run_index} dose image written") and is_ok

        run_value_memory = get_single_voxel_value_from_image(run_image_memory)
        run_value_disk = read_single_voxel_value(run_image_path)

        b = np.isclose(run_value_memory, run_value_disk, rtol=1e-6, atol=0.0)
        is_ok = (
            utility.print_test(
                b,
                f"Run {run_index} dose value in memory vs disk: "
                f"{run_value_memory:.6e} {run_value_disk:.6e}",
            )
            and is_ok
        )

        dose_values_from_memory.append(run_value_memory)
        dose_values_from_disk.append(run_value_disk)

        run_stats_item = stats.user_output.stats.data_per_run[
            run_index
        ].get_data_item_object(0)
        run_stats_path = stats.stats.get_output_path(which=run_index)

        b = run_stats_path.is_file()
        is_ok = (
            utility.print_test(b, f"Run {run_index} statistics file written") and is_ok
        )

        run_stats_from_disk = utility.read_stats_file(run_stats_path)
        run_stats_disk_item = (
            run_stats_from_disk.user_output.stats.merged_data.get_data_item_object(0)
        )

        b = run_stats_item.events == n_primaries
        is_ok = (
            utility.print_test(
                b,
                f"Run {run_index} statistics events vs expected primaries: "
                f"{run_stats_item.events} {n_primaries}",
            )
            and is_ok
        )

        b = run_stats_item.runs == 1
        is_ok = (
            utility.print_test(
                b,
                f"Run {run_index} statistics runs: {run_stats_item.runs} 1",
            )
            and is_ok
        )

        b = run_stats_disk_item.events == n_primaries
        is_ok = (
            utility.print_test(
                b,
                f"Run {run_index} statistics file events vs expected primaries: "
                f"{run_stats_disk_item.events} {n_primaries}",
            )
            and is_ok
        )

        b = run_stats_disk_item.runs == 1
        is_ok = (
            utility.print_test(
                b,
                f"Run {run_index} statistics file runs: {run_stats_disk_item.runs} 1",
            )
            and is_ok
        )

        b = run_stats_disk_item.events == run_stats_item.events
        is_ok = (
            utility.print_test(
                b,
                f"Run {run_index} statistics file vs memory events: "
                f"{run_stats_disk_item.events} {run_stats_item.events}",
            )
            and is_ok
        )

        b = run_stats_disk_item.tracks == run_stats_item.tracks
        is_ok = (
            utility.print_test(
                b,
                f"Run {run_index} statistics file vs memory tracks: "
                f"{run_stats_disk_item.tracks} {run_stats_item.tracks}",
            )
            and is_ok
        )

        b = run_stats_disk_item.steps == run_stats_item.steps
        is_ok = (
            utility.print_test(
                b,
                f"Run {run_index} statistics file vs memory steps: "
                f"{run_stats_disk_item.steps} {run_stats_item.steps}",
            )
            and is_ok
        )

    merged_image_memory = dose.dose.get_data(which="merged")
    merged_image_path = dose.dose.get_output_path(which="merged")

    b = merged_image_path.is_file()
    is_ok = utility.print_test(b, "Merged dose image written") and is_ok

    merged_value_memory = get_single_voxel_value_from_image(merged_image_memory)
    merged_value_disk = read_single_voxel_value(merged_image_path)

    b = np.isclose(merged_value_memory, merged_value_disk, rtol=1e-6, atol=0.0)
    is_ok = (
        utility.print_test(
            b,
            "Merged dose value in memory vs disk: "
            f"{merged_value_memory:.6e} {merged_value_disk:.6e}",
        )
        and is_ok
    )

    dose_per_primary = [
        dose_value / n_primaries
        for dose_value, n_primaries in zip(dose_values_from_disk, expected_primaries)
    ]
    mean_dose_per_primary = float(np.mean(dose_per_primary))

    # Because the scoring geometry is the same in each run, the deposited dose
    # per primary should be consistent across runs up to Monte Carlo
    # fluctuations.
    for run_index, value in enumerate(dose_per_primary):
        relative_deviation = abs(value - mean_dose_per_primary) / mean_dose_per_primary
        b = relative_deviation < 0.08
        is_ok = (
            utility.print_test(
                b,
                f"Run {run_index} dose per primary relative deviation: "
                f"{relative_deviation:.3%}",
            )
            and is_ok
        )

    sum_of_run_doses = float(sum(dose_values_from_disk))
    b = np.isclose(sum_of_run_doses, merged_value_disk, rtol=1e-6, atol=0.0)
    is_ok = (
        utility.print_test(
            b,
            f"Sum of per-run dose values vs merged dose value: "
            f"{sum_of_run_doses:.6e} {merged_value_disk:.6e}",
        )
        and is_ok
    )

    # Check merged statistics against both the written output and the expected
    # total number of primaries. Also verify that the merged counters match the
    # sum over the per-run statistics snapshots kept by the actor output.
    stats_output_path = stats.get_output_path()
    b = stats_output_path.is_file()
    is_ok = utility.print_test(b, "Merged statistics file written") and is_ok

    stats_from_disk = utility.read_stats_file(stats_output_path)
    is_ok = utility.assert_stats(stats, stats_from_disk, tolerance=1e-6) and is_ok

    stats_counts = stats.user_output.stats.merged_data.get_data_item_object()
    expected_total_primaries = sum(expected_primaries)
    summed_run_events = 0
    summed_run_tracks = 0
    summed_run_steps = 0
    for run_index in range(len(expected_primaries)):
        run_stats_item = stats.user_output.stats.data_per_run[
            run_index
        ].get_data_item_object()
        summed_run_events += run_stats_item.events
        summed_run_tracks += run_stats_item.tracks
        summed_run_steps += run_stats_item.steps

    b = stats_counts.events == expected_total_primaries
    is_ok = (
        utility.print_test(
            b,
            f"Merged statistics events vs expected primaries: "
            f"{stats_counts.events} {expected_total_primaries}",
        )
        and is_ok
    )

    b = stats_counts.runs == len(expected_primaries)
    is_ok = (
        utility.print_test(
            b,
            f"Merged statistics runs vs number of timing intervals: "
            f"{stats_counts.runs} {len(expected_primaries)}",
        )
        and is_ok
    )

    b = stats_counts.events == summed_run_events
    is_ok = (
        utility.print_test(
            b,
            f"Merged statistics events vs sum of per-run events: "
            f"{stats_counts.events} {summed_run_events}",
        )
        and is_ok
    )

    b = stats_counts.tracks == summed_run_tracks
    is_ok = (
        utility.print_test(
            b,
            f"Merged statistics tracks vs sum of per-run tracks: "
            f"{stats_counts.tracks} {summed_run_tracks}",
        )
        and is_ok
    )

    b = stats_counts.steps == summed_run_steps
    is_ok = (
        utility.print_test(
            b,
            f"Merged statistics steps vs sum of per-run steps: "
            f"{stats_counts.steps} {summed_run_steps}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)

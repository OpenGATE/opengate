#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil

import opengate as gate
from opengate.tests import utility

from opengate.tests.src.geometry.test009_voxels_dynamic_helpers import (
    build_dynamic_voxel_simulation,
    get_dynamic_patient_images,
    merge_images_from_jobs,
    merge_stats_from_jobs,
    wait_for_completed_jobs,
)


def run_split_campaign(paths, split_path, backend, backend_options=None):
    sec = gate.g4_units.s
    run_timing_intervals = [(0, 0.5 * sec), (0.5 * sec, 1 * sec)]
    dynamic_image_paths = [
        paths.data / "patient-4mm.mhd",
        paths.data / "patient-4mm.mhd",
    ]

    sim, _, _, _ = build_dynamic_voxel_simulation(
        paths,
        split_path.parent / f"{split_path.name}_master_input",
        run_timing_intervals,
        dynamic_image_paths=dynamic_image_paths,
    )

    split_root = gate.jobs_split(
        sim,
        3,
        split_path,
        policy="split_in_time_total",
    )
    summary = gate.jobs_run(
        split_root,
        backend=backend,
        backend_options=backend_options,
    )
    checks_ok = utility.print_test(
        summary["submitted_jobs"] == 3,
        f"{backend} submitted split jobs: {summary}",
    )

    status_data = wait_for_completed_jobs(split_root, expected_count=3)
    manifest_jobs = status_data["jobs"]
    job_folders = []

    expected_job_intervals = {
        1: [[0.0 * sec, 1.0 / 3.0 * sec]],
        2: [[1.0 / 3.0 * sec, 0.5 * sec], [0.5 * sec, 2.0 / 3.0 * sec]],
        3: [[2.0 / 3.0 * sec, 1.0 * sec]],
    }
    expected_job_images = {
        1: [dynamic_image_paths[0]],
        2: [dynamic_image_paths[0], dynamic_image_paths[1]],
        3: [dynamic_image_paths[1]],
    }

    for job in manifest_jobs:
        job_index = job["job_index"]
        job_folder = split_root / job["folder_name"]
        job_folders.append(job_folder)
        child_simulation = gate.create_sim_from_json(job_folder / "simulation.json")
        child_dynamic_images = get_dynamic_patient_images(child_simulation)
        expected_dynamic_images = expected_job_images[job_index]

        # split_in_time_total should preserve the global active timeline. The
        # middle child bridges the two original runs and must therefore keep
        # both dynamic image entries.
        checks_ok = (
            utility.print_test(
                child_simulation.run_timing_intervals
                == expected_job_intervals[job_index],
                f"{backend} {job['folder_name']} run timing intervals: {child_simulation.run_timing_intervals}",
            )
            and checks_ok
        )
        checks_ok = (
            utility.print_test(
                child_dynamic_images == expected_dynamic_images,
                f"{backend} {job['folder_name']} dynamic images: {child_dynamic_images}",
            )
            and checks_ok
        )

    merged_stats_path = paths.output / f"{split_path.name}_{backend}_merged_stats.json"
    merged_dose_path = paths.output / f"{split_path.name}_{backend}_merged_edep.mhd"

    merged_stats = merge_stats_from_jobs(job_folders, merged_stats_path)
    merge_images_from_jobs(job_folders, merged_dose_path)

    stats_ref = utility.read_stats_file(paths.gate_output / "stat.txt")
    checks_ok = (
        utility.assert_stats_json(
            merged_stats.user_output.stats,
            stats_ref.user_output.stats,
            tolerance=0.15,
            track_types_flag=True,
        )
        and checks_ok
    )
    checks_ok = (
        utility.assert_images(
            paths.gate_output / "output-Edep.mhd",
            merged_dose_path,
            merged_stats,
            tolerance=35,
            ignore_value_data2=0,
            apply_ignore_mask_to_sum_check=False,
        )
        and checks_ok
    )

    return checks_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test009_voxels", "test009")
    is_ok = True

    shutil.rmtree(paths.output, ignore_errors=True)

    is_ok = (
        run_split_campaign(
            paths,
            paths.output / "split_campaign_sequential",
            backend="local_sequential",
        )
        and is_ok
    )
    is_ok = (
        run_split_campaign(
            paths,
            paths.output / "split_campaign_pool",
            backend="local_pool",
            backend_options={
                # Run 3 jobs with 2 workers so the pooled backend also covers
                # queued execution instead of a trivial 1:1 worker-to-job map.
                "n_workers": 2,
                "start_method": "spawn",
                "maxtasksperchild": 1,
            },
        )
        and is_ok
    )

    utility.test_ok(is_ok)

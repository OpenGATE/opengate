#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import shutil

import opengate as gate
from opengate.tests import utility

from opengate.tests.src.geometry.test019_phsp_actor_helpers import (
    build_phsp_actor_simulation,
    check_child_phase_space_time_medians,
    check_merged_phase_space_time_median,
    compare_phase_space_roots,
    merge_phase_space_root_from_jobs,
    merge_stats_from_jobs,
)
from opengate.tests.src.geometry.test009_voxels_dynamic_helpers import (
    wait_for_completed_jobs,
)


def pretty_json(data):
    return json.dumps(data, indent=2, sort_keys=True)


def run_split_campaign(
    paths,
    split_path,
    backend,
    run_timing_intervals,
    reference_stats,
    reference_root,
    backend_options=None,
):
    sim, _, _, _ = build_phsp_actor_simulation(
        split_path.parent / f"{split_path.name}_master_input",
        run_timing_intervals,
        source_activity=1000,
        random_seed=321654,
    )

    split_root = gate.jobs_split(
        sim,
        3,
        split_path,
        policy="split_time_total",
    )
    summary = gate.jobs_run(
        split_root,
        backend=backend,
        backend_options=backend_options,
    )
    is_ok = utility.print_test(
        summary["submitted_jobs"] == 3,
        f"{backend} submitted split jobs:\n{pretty_json(summary)}",
    )

    deadline_status = wait_for_completed_jobs(split_root, expected_count=3)
    job_folders = [
        split_root / job["folder_name"] for job in deadline_status.get("jobs", [])
    ]

    merged_stats_path = paths.output / f"{split_path.name}_{backend}_merged_stats.txt"
    merged_root_path = paths.output / f"{split_path.name}_{backend}_merged.root"
    merged_stats = merge_stats_from_jobs(job_folders, merged_stats_path)
    merge_phase_space_root_from_jobs(job_folders, merged_root_path)

    is_ok = utility.assert_stats(
        merged_stats,
        reference_stats,
        tolerance=0.15,
    ) and is_ok
    is_ok = check_child_phase_space_time_medians(job_folders) and is_ok
    is_ok = (
        check_merged_phase_space_time_median(merged_root_path, run_timing_intervals)
        and is_ok
    )
    is_ok = compare_phase_space_roots(reference_root, merged_root_path) and is_ok
    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test019")
    sec = gate.g4_units.s
    is_ok = True
    run_timing_intervals = [(0.0 * sec, 1.0 * sec)]

    shutil.rmtree(paths.output / "jobs_split", ignore_errors=True)
    reference_output = paths.output / "split_reference"
    shutil.rmtree(reference_output, ignore_errors=True)

    reference_sim, _, reference_stats_actor, reference_phsp_actor = (
        build_phsp_actor_simulation(
            reference_output,
            run_timing_intervals,
            source_activity=1000,
            random_seed=321654,
        )
    )
    reference_sim.run(start_new_process=True)
    reference_stats = utility.read_stats_file(reference_output / "stats.txt")
    reference_root = reference_output / reference_phsp_actor.output_filename

    is_ok = run_split_campaign(
        paths,
        paths.output / "jobs_split" / "split_campaign_sequential",
        backend="local_sequential",
        run_timing_intervals=run_timing_intervals,
        reference_stats=reference_stats,
        reference_root=reference_root,
    ) and is_ok
    is_ok = run_split_campaign(
        paths,
        paths.output / "jobs_split" / "split_campaign_pool",
        backend="local_pool",
        run_timing_intervals=run_timing_intervals,
        reference_stats=reference_stats,
        reference_root=reference_root,
        backend_options={
            "n_workers": 2,
            "start_method": "spawn",
            "maxtasksperchild": 1,
        },
    ) and is_ok

    utility.test_ok(is_ok)

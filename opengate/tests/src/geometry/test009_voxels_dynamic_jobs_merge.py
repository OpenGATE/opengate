#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test 009 (jobs_merge variant): Dynamic voxel simulation split, run, and merged
through GATE's merge machinery.

Objective:
Validate that a time-split dynamic voxel simulation can be:
- split into child jobs with ``jobs_split(...)``,
- executed through ``jobs_run(...)``,
- and merged back with ``jobs_merge(...)``

while preserving both:
- the split-time structural information in the children
  (run timing intervals and dynamic image selections),
- and the merged physics outputs
  (statistics actor output and dose image output).

This test is functionally equivalent to the existing manual-merge variant, but
it exercises GATE's hierarchical merge path instead of summing files manually.

Minimal user workflow example:

```python
import opengate as gate

sim = gate.Simulation()
# ... configure geometry, sources, actors, run timing intervals ...

jobs_split_manager = gate.jobs_split(
    simulation=sim,
    number_of_jobs=3,
    campaign_dir="my_split_campaign",
    policy="split_in_time_total",
)
split_root = jobs_split_manager.campaign_dir

gate.jobs_run(
    split_root,
    backend="local_pool",
    number_of_workers=2,
)

# ... wait until all jobs have completed ...

gate.jobs_merge(
    split_root,
    to_path="my_merged_campaign",
)
```
"""

import shutil

import opengate as gate
from opengate.tests import utility

from opengate.tests.src.geometry.test009_voxels_dynamic_helpers import (
    build_dynamic_voxel_simulation,
    get_dynamic_patient_images,
    wait_for_completed_jobs,
)


def run_split_campaign(paths, split_path, merge_path, backend, number_of_workers=None):
    sec = gate.g4_units.s
    run_timing_intervals = [(0, 0.4 * sec), (0.4 * sec, 1 * sec)]
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
        simulation=sim,
        number_of_jobs=3,
        campaign_dir=split_path,
        policy="split_in_time_total",
    ).campaign_dir
    gate.print_jobs_split_summary(split_path)
    summary = gate.jobs_run(
        split_root,
        backend=backend,
        number_of_workers=number_of_workers,
    )
    checks_ok = utility.print_test(
        summary["submitted_jobs"] == 3,
        f"{backend} submitted split jobs: {summary}",
    )

    status_data = wait_for_completed_jobs(split_root, expected_count=3)
    manifest_jobs = status_data["jobs"]

    expected_job_intervals = {
        1: [[0.0 * sec, 1.0 / 3.0 * sec]],
        2: [[1.0 / 3.0 * sec, 0.4 * sec], [0.4 * sec, 2.0 / 3.0 * sec]],
        3: [[2.0 / 3.0 * sec, 1.0 * sec]],
    }
    expected_job_images = {
        1: [dynamic_image_paths[0].name],
        2: [dynamic_image_paths[0].name, dynamic_image_paths[1].name],
        3: [dynamic_image_paths[1].name],
    }

    for job in manifest_jobs:
        job_index = job["job_index"]
        job_folder = split_root / job["folder_name"]
        child_simulation = gate.create_sim_from_json(job_folder / "simulation.json")
        child_dynamic_images = get_dynamic_patient_images(child_simulation)
        expected_dynamic_images = expected_job_images[job_index]
        child_dynamic_image_names = [path.name for path in child_dynamic_images]
        child_dynamic_images_are_job_local = all(
            path.parent == job_folder for path in child_dynamic_images
        )

        # split_in_time_total should preserve the global active timeline. The
        # middle child bridges the two original runs and must therefore keep
        # both dynamic image entries. Input paths are transferred into each job
        # folder, so the value check compares the selected image names and then
        # verifies that the rehydrated paths are job-local.
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
                child_dynamic_image_names == expected_dynamic_images
                and child_dynamic_images_are_job_local,
                f"{backend} {job['folder_name']} dynamic images: {child_dynamic_images}",
            )
            and checks_ok
        )

    merge_manager = gate.jobs_merge(split_root, to_path=merge_path)
    merge_manager.print_merge_summary()
    checks_ok = (
        utility.print_test(
            merge_manager.merge_result["number_of_leaf_sources"] == 3,
            f"{backend} merged split jobs: {merge_manager.merge_result}",
        )
        and checks_ok
    )

    merged_stats = utility.read_stats_file(merge_path / "stats.txt")
    # Keep the merged stats comparable to the historical test009 reference,
    # which treats the whole simulation as one run even though several timing
    # intervals were used internally.
    merged_stats.counts.runs = 1
    stats_ref = utility.read_stats_file(paths.gate_output / "stat.txt")
    checks_ok = utility.assert_stats(merged_stats, stats_ref, 0.15) and checks_ok
    checks_ok = (
        utility.assert_images(
            paths.gate_output / "output-Edep.mhd",
            merge_path / "test009-edep_edep.mhd",
            merged_stats,
            tolerance=35,
            ignore_value_data2=0,
            apply_ignore_mask_to_sum_check=False,
        )
        and checks_ok
    )

    return checks_ok


if __name__ == "__main__":
    # Use a jobs-specific output folder so this test can run concurrently with
    # the other test009 variants under opengate_tests without deleting their
    # campaigns or intermediate output.
    paths = utility.get_default_test_paths(
        __file__, "gate_test009_voxels", "test009_jobs_merge"
    )
    is_ok = True

    shutil.rmtree(paths.output, ignore_errors=True)

    is_ok = (
        run_split_campaign(
            paths,
            paths.output / "split_campaign_sequential",
            paths.output / "merged_campaign_sequential",
            backend="local_sequential",
        )
        and is_ok
    )
    is_ok = (
        run_split_campaign(
            paths,
            paths.output / "split_campaign_pool",
            paths.output / "merged_campaign_pool",
            backend="local_pool",
            # Run 3 jobs with 2 workers so the pooled backend also covers
            # queued execution instead of a trivial 1:1 worker-to-job map.
            number_of_workers=2,
        )
        and is_ok
    )

    utility.test_ok(is_ok)

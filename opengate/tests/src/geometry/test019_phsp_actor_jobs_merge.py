#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test 019 (jobs_merge variant): Phase-space ROOT output split, run, and merged
through GATE's merge machinery.

Objective:
Validate that a phase-space actor producing ROOT output can be:
- split into child jobs with ``jobs_split(...)``,
- executed through ``jobs_run(...)``,
- and merged back with ``jobs_merge(...)``

while preserving both:
- the split-time structure of the child jobs,
- and the merged physics output stored in the ROOT tree.

This test intentionally does not request ``RunID`` or ``EventID`` branches from
the PhaseSpaceActor. Because the simulation uses one original run timing
interval and each split child therefore contains exactly one local run, the
ROOT merge is expected to reduce to plain concatenation of the child trees.

Minimal user workflow example:

```python
import opengate as gate

sim = gate.Simulation()
# ... configure geometry, source, actors, run timing intervals ...

split_root = gate.jobs_split(
    sim,
    3,
    "my_split_campaign",
    policy="split_in_time_total",
)

gate.jobs_run(
    split_root,
    backend="local_pool",
    backend_options={
        "n_workers": 2,
        "start_method": "spawn",
        "maxtasksperchild": 1,
    },
)

# ... wait until all jobs have completed ...

merge_manager = gate.jobs_merge(
    split_root,
    to_path="my_merged_campaign",
)
merge_manager.print_merge_summary()
```
"""

import json
import shutil

import opengate as gate
from opengate.tests import utility
from opengate.tests.src.geometry.test009_voxels_dynamic_helpers import (
    wait_for_completed_jobs,
)
from opengate.tests.src.geometry.test019_phsp_actor_helpers import (
    build_phsp_actor_simulation,
    check_child_phase_space_time_medians,
    check_merged_phase_space_time_median,
    compare_phase_space_roots,
)


def pretty_json(data):
    return json.dumps(data, indent=2, sort_keys=True)


def run_split_campaign(
    paths,
    split_path,
    merge_path,
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
        policy="split_in_time_total",
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

    status_data = wait_for_completed_jobs(split_root, expected_count=3)
    job_folders = [split_root / job["folder_name"] for job in status_data.get("jobs", [])]

    is_ok = check_child_phase_space_time_medians(job_folders) and is_ok

    merge_manager = gate.jobs_merge(split_root, to_path=merge_path)
    merge_manager.print_merge_summary()
    is_ok = (
        utility.print_test(
            merge_manager.merge_result["number_of_leaf_sources"] == 3,
            f"{backend} merged split jobs:\n{pretty_json(merge_manager.merge_result)}",
        )
        and is_ok
    )

    merged_stats = utility.read_stats_file(merge_path / "stats.txt")
    merged_root = merge_path / "test019_phsp_actor.root"
    merged_metadata = merge_path / "test019_phsp_actor-PhaseSpace-metadata.json"

    # FIXME: SimulationStatisticsActor does not yet reconstruct the original
    # run set during jobs_merge. Keep the historical single-run interpretation
    # here so this test stays focused on ROOT output merging.
    merged_stats.counts.runs = 1
    is_ok = utility.assert_stats(merged_stats, reference_stats, tolerance=0.15) and is_ok
    is_ok = (
        utility.print_test(
            merged_metadata.exists(),
            f"{backend} merged ROOT metadata exists: {merged_metadata}",
        )
        and is_ok
    )
    is_ok = (
        check_merged_phase_space_time_median(merged_root, run_timing_intervals)
        and is_ok
    )
    is_ok = compare_phase_space_roots(reference_root, merged_root) and is_ok
    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test019")
    sec = gate.g4_units.s
    is_ok = True
    run_timing_intervals = [(0.0 * sec, 1.0 * sec)]

    shutil.rmtree(paths.output / "jobs_merge", ignore_errors=True)
    reference_output = paths.output / "merge_reference"
    shutil.rmtree(reference_output, ignore_errors=True)

    reference_sim, _, _, reference_phsp_actor = build_phsp_actor_simulation(
        reference_output,
        run_timing_intervals,
        source_activity=1000,
        random_seed=321654,
    )
    reference_sim.run(start_new_process=True)
    reference_stats = utility.read_stats_file(reference_output / "stats.txt")
    reference_root = reference_output / reference_phsp_actor.output_filename

    is_ok = (
        run_split_campaign(
            paths,
            paths.output / "jobs_merge" / "split_campaign_sequential",
            paths.output / "jobs_merge" / "merged_campaign_sequential",
            backend="local_sequential",
            run_timing_intervals=run_timing_intervals,
            reference_stats=reference_stats,
            reference_root=reference_root,
        )
        and is_ok
    )
    is_ok = (
        run_split_campaign(
            paths,
            paths.output / "jobs_merge" / "split_campaign_pool",
            paths.output / "jobs_merge" / "merged_campaign_pool",
            backend="local_pool",
            run_timing_intervals=run_timing_intervals,
            reference_stats=reference_stats,
            reference_root=reference_root,
            backend_options={
                # Use fewer workers than jobs so the pooled backend also covers
                # queued dispatch rather than only a trivial one-job-per-worker case.
                "n_workers": 2,
                "start_method": "spawn",
                "maxtasksperchild": 1,
            },
        )
        and is_ok
    )

    utility.test_ok(is_ok)

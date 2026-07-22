#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil

import opengate as gate
from opengate.tests import utility

from opengate.tests.src.misc.test111_helpers_wip import (
    build_simple_simulation,
    load_execution_status,
    load_manifest,
    wait_until_execution_status,
)

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test111_pool")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True

    sim = build_simple_simulation(paths.output / "pool_input")
    split_root = gate.jobs_split(
        sim, 2, paths.output / "pool_campaign", policy="split_time"
    )

    summary = gate.jobs_run(
        split_root,
        backend="local_pool",
        backend_options={
            "pooling_options": {
                "n_workers": 2,
                "start_method": "spawn",
                "maxtasksperchild": 1,
            }
        },
    )
    is_ok = is_ok and utility.print_test(
        summary["submitted_jobs"] == 2 and summary["campaign_process_pid"] is not None,
        f"local_pool submission summary: {summary}",
    )

    wait_until_execution_status(split_root, "completed", 2)
    manifest = load_manifest(split_root)
    for job in manifest["jobs"]:
        job_folder = split_root / job["folder_name"]
        status = load_execution_status(job_folder)
        is_ok = is_ok and utility.print_test(
            status is not None
            and status["status"] == "completed"
            and status["backend"] == "local_pool",
            f"local_pool execution status for {job['folder_name']}: {status}",
        )

    utility.test_ok(is_ok)

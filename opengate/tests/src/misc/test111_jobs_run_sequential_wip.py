#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil

import opengate as gate
from opengate.tests import utility

from opengate.tests.src.misc.test111_helpers_wip import (
    load_backend_status,
    build_simple_simulation,
    load_execution_status,
    load_manifest,
    wait_until_execution_status,
    write_execution_status,
)

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test111_seq")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True

    sim = build_simple_simulation(paths.output / "sequential_input")
    split_root = gate.jobs_split(
        sim, 2, paths.output / "sequential_campaign", policy="split_time"
    )

    summary = gate.jobs_run(split_root, backend="local_sequential")
    is_ok = is_ok and utility.print_test(
        summary["submitted_jobs"] == 2
        and summary["skipped_completed_jobs"] == 0
        and summary["campaign_process_pid"] is not None,
        f"local_sequential submission summary: {summary}",
    )
    backend_status = load_backend_status(split_root)
    is_ok = is_ok and utility.print_test(
        backend_status is not None
        and backend_status["backend"] == "local_sequential"
        and backend_status["status"] == "submitted"
        and backend_status["submitted_jobs"] == 2
        and backend_status["campaign_process_pid"] == summary["campaign_process_pid"],
        f"local backend status: {backend_status}",
    )

    wait_until_execution_status(split_root, "completed", 2)
    manifest = load_manifest(split_root)
    for job in manifest["jobs"]:
        job_folder = split_root / job["folder_name"]
        status = load_execution_status(job_folder)
        is_ok = is_ok and utility.print_test(
            status is not None
            and status["status"] == "completed"
            and status["backend"] == "local_sequential",
            f"local_sequential execution status for {job['folder_name']}: {status}",
        )

    summary_second = gate.jobs_run(split_root, backend="local_sequential")
    is_ok = is_ok and utility.print_test(
        summary_second["submitted_jobs"] == 0
        and summary_second["skipped_completed_jobs"] == 2
        and summary_second["campaign_process_pid"] is None,
        f"local_sequential skip-completed summary: {summary_second}",
    )

    first_job_folder = split_root / manifest["jobs"][0]["folder_name"]
    running_status = load_execution_status(first_job_folder)
    running_status["status"] = "running"
    write_execution_status(first_job_folder, running_status)

    running_failure_detected = False
    try:
        gate.jobs_run(split_root, backend="local_sequential")
    except Exception as error:
        running_failure_detected = "restart_running_jobs=True" in str(error)

    is_ok = is_ok and utility.print_test(
        running_failure_detected,
        "jobs_run detects running jobs and asks for restart_running_jobs=True",
    )

    summary_restart = gate.jobs_run(
        split_root,
        backend="local_sequential",
        restart_running_jobs=True,
    )
    is_ok = is_ok and utility.print_test(
        summary_restart["submitted_jobs"] == 1
        and summary_restart["skipped_completed_jobs"] == 1,
        f"local_sequential restart-running summary: {summary_restart}",
    )
    wait_until_execution_status(split_root, "completed", 2)

    utility.test_ok(is_ok)

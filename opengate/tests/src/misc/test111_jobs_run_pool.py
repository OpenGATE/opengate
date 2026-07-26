#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import shutil

import opengate as gate
from opengate.tests import utility

from opengate.tests.src.misc.test111_helpers import (
    load_backend_status,
    build_simple_simulation,
    load_execution_status,
    load_manifest,
    wait_until_execution_counts,
    wait_until_execution_status,
    write_execution_status,
)


def pretty_json(data):
    return json.dumps(data, indent=2, sort_keys=True)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test111_pool")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True

    sim = build_simple_simulation(paths.output / "pool_input")
    split_root = gate.jobs_split(
        sim, 4, paths.output / "pool_campaign", policy="split_in_time_per_run"
    )

    summary = gate.jobs_run(
        split_root,
        backend="local_pool",
        backend_options={
            "n_workers": 3,
            "start_method": "spawn",
            "maxtasksperchild": 1,
        },
    )
    is_ok = is_ok and utility.print_test(
        summary["submitted_jobs"] == 4
        and summary["skipped_completed_jobs"] == 0
        and summary["campaign_process_pid"] is not None,
        f"local_pool submission summary:\n{pretty_json(summary)}",
    )
    backend_status = load_backend_status(split_root)
    is_ok = is_ok and utility.print_test(
        backend_status is not None
        and backend_status["backend"] == "local_pool"
        and backend_status["status"] == "submitted"
        and backend_status["submitted_jobs"] == 4
        and backend_status["campaign_process_pid"] == summary["campaign_process_pid"],
        f"local_pool backend status:\n{pretty_json(backend_status)}",
    )

    first_job_folder = split_root / "job0001"
    wait_until_execution_status(split_root, "completed", 4)
    manifest = load_manifest(split_root)
    for job in manifest["jobs"]:
        job_folder = split_root / job["folder_name"]
        status = load_execution_status(job_folder)
        is_ok = is_ok and utility.print_test(
            status is not None
            and status["status"] == "completed"
            and status["backend"] == "local_pool",
            f"local_pool execution status for {job['folder_name']}:\n{pretty_json(status)}",
        )

    summary_second = gate.jobs_run(
        split_root,
        backend="local_pool",
        backend_options={
            "n_workers": 3,
            "start_method": "spawn",
            "maxtasksperchild": 1,
        },
    )
    is_ok = is_ok and utility.print_test(
        summary_second["submitted_jobs"] == 0
        and summary_second["skipped_completed_jobs"] == 4
        and summary_second["campaign_process_pid"] is None,
        f"local_pool skip-completed summary:\n{pretty_json(summary_second)}",
    )

    running_status = load_execution_status(first_job_folder)
    running_status["status"] = "running"
    write_execution_status(first_job_folder, running_status)

    running_failure_detected = False
    try:
        gate.jobs_run(
            split_root,
            backend="local_pool",
            backend_options={
                "n_workers": 3,
                "start_method": "spawn",
                "maxtasksperchild": 1,
            },
        )
    except Exception as error:
        running_failure_detected = "restart_running_jobs=True" in str(error)

    is_ok = is_ok and utility.print_test(
        running_failure_detected,
        "jobs_run detects a persisted running job and asks for restart_running_jobs=True",
    )

    print(
        "Intentionally corrupting job0002/simulation.json to verify that the pool backend "
        "reports a failed child run when simulation deserialization breaks."
    )
    broken_simulation_path = split_root / "job0002" / "simulation.json"
    with open(broken_simulation_path, "w") as output_file:
        json.dump({"broken": "json"}, output_file)

    summary_failed = gate.jobs_run(
        split_root,
        backend="local_pool",
        backend_options={
            "n_workers": 3,
            "start_method": "spawn",
            "maxtasksperchild": 1,
        },
        force=True,
        restart_running_jobs=True,
    )
    is_ok = is_ok and utility.print_test(
        summary_failed["submitted_jobs"] == 4
        and summary_failed["skipped_completed_jobs"] == 0,
        f"local_pool forced rerun summary:\n{pretty_json(summary_failed)}",
    )

    # The invalid simulation.json above is expected to make job0002 fail during
    # create_sim_from_json(...). This exercises failed-run reporting for the
    # pool backend using a realistic framework-internal failure mode.
    wait_until_execution_counts(split_root, {"completed": 3, "failed": 1})
    failed_status = load_execution_status(split_root / "job0002")
    is_ok = is_ok and utility.print_test(
        failed_status is not None
        and failed_status["status"] == "failed"
        and failed_status["backend"] == "local_pool"
        and len(failed_status.get("error_message", "")) > 0,
        f"local_pool failed execution status for job0002:\n{pretty_json(failed_status)}",
    )

    utility.test_ok(is_ok)

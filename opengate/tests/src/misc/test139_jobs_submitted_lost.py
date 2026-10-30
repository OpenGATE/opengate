#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 139: states 'submitted' and 'lost' of the jobs, for all the backends
(only the files of the campaign are read, no query of the scheduler).

A campaign of 3 jobs is submitted to a fake slurm (a script that prints
"Submitted batch job 4242" and runs nothing):
1. the 3 jobs are 'submitted', with the scheduler job id; JOBDIR added to the
   --export option of sbatch (not to the last option)
2. job 1 runs (job runner): 'completed', submission time and scheduler job
   id kept
3. job 2 is 'running' but its last progress is old: 'lost' (10 min while
   simulating events, 1 h before, e.g. initialization)
4. jobs_run again: the lost job is submitted again, not the completed one;
   a job still 'submitted' (waiting in the queue) is not
5. progress of the campaign: fraction of the events, estimated end of the
   running jobs (elapsed time and fraction of the running job)
6. merge of a campaign moved from another computer: its output_dir (e.g.
   /lustre/...) cannot be created here, clear error (use -o); local backend:
   default number of workers at most the number of cores
7. cancel: slurm (fake scancel with the job ids), local (the process of a
   running job is stopped); the jobs are 'cancelled', the completed one
   kept, and run again by jobs_run
"""

import os
import socket
import subprocess
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

import opengate as gate
from opengate.jobs import (
    jobs_split,
    jobs_run,
    jobs_cancel,
    jobs_status,
    load_job_execution_status,
    _run_job_folder_cli,
    _check_merge_output_dir,
    _get_default_number_of_workers,
    _load_jobs_manifest,
    JOB_PROGRESS_FILENAME,
    JOB_EXECUTION_STATUS_FILENAME,
)
from opengate.exception import GateMergeError
from opengate.tests import utility


def create_simulation(output_dir):
    sim = gate.Simulation()
    sim.output_dir = output_dir
    sim.number_of_threads = 1
    sim.random_seed = 123
    m = gate.g4_units.m
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [20 * gate.g4_units.cm] * 3
    waterbox.material = "G4_WATER"
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140 * gate.g4_units.keV
    source.activity = 2000 * gate.g4_units.Bq
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "stats.txt"
    sim.run_timing_intervals = [[0, 1 * gate.g4_units.s]]
    return sim


def write_old_progress(job_folder, status, minutes):
    t = (datetime.now() - timedelta(minutes=minutes)).isoformat()
    with open(job_folder / JOB_PROGRESS_FILENAME, "w") as f:
        json.dump({"status": status, "generated_events": 10, "updated_at": t}, f)


def set_execution_status(job_folder, status):
    path = job_folder / JOB_EXECUTION_STATUS_FILENAME
    with open(path) as f:
        data = json.load(f)
    data["status"] = status
    with open(path, "w") as f:
        json.dump(data, f)


def execution_statuses(campaign_dir):
    status = jobs_status(campaign_dir, check_inputs=False)
    jobs = sorted(status["jobs"], key=lambda j: j["job_index"])
    return [j["execution_status"] for j in jobs], status


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test139")
    campaign_dir = paths.output / "campaign"

    # fake slurm: prints the job id, runs nothing
    fake_sbatch = paths.output / "fake_sbatch.sh"
    fake_sbatch.parent.mkdir(parents=True, exist_ok=True)
    fake_sbatch.write_text('#!/bin/sh\necho "Submitted batch job 4242"\n')
    os.chmod(fake_sbatch, 0o755)
    backend_options = {
        "submit_binary": str(fake_sbatch),
        "submit_filename": "job.slurm",
        # (JOBDIR is added to --export, whatever the order of the options)
        "command_line_args": ["--export=ALL", "--time=01:00:00"],
    }

    sim = create_simulation(campaign_dir / "output")
    jobs_split(
        simulation=sim,
        campaign_dir=campaign_dir,
        number_of_jobs=3,
        overwrite_existing_job_folders=True,
    )
    job_folders = [campaign_dir / f"job{i:04d}" for i in (1, 2, 3)]

    # 1. submitted, with the scheduler job id
    result = jobs_run(campaign_dir, backend="slurm", backend_options=backend_options)
    statuses, status = execution_statuses(campaign_dir)
    ids = [load_job_execution_status(f).get("scheduler_job_id") for f in job_folders]
    print(f"After submission: {statuses}, scheduler ids {ids}")
    command = result["submission_command"]
    print(f"Submit command of the first job: {command}")
    is_ok = utility.print_test(
        f"--export=ALL,JOBDIR={job_folders[0]}" in command
        and "--time=01:00:00" in command
        and command[-1] == "job.slurm"
        and result["submitted_jobs"] == 3
        and statuses == ["submitted"] * 3
        and ids == ["4242"] * 3
        and status["execution_counts"]["submitted"] == 3,
        "1. jobs submitted, with the scheduler job id",
    )

    # 2. job 1 runs: completed, submission time and id kept
    before = load_job_execution_status(job_folders[0])
    _run_job_folder_cli(job_folders[0], backend="slurm")
    after = load_job_execution_status(job_folders[0])
    print(f"Job 1: {before['status']} -> {after['status']}")
    is_ok = (
        utility.print_test(
            after["status"] == "completed"
            and after["scheduler_job_id"] == "4242"
            and after["submitted_at"] == before["submitted_at"]
            and after["started_at"] is not None,
            "2. job run: completed, submission time and scheduler id kept",
        )
        and is_ok
    )

    # 3. job 2 running, old progress: lost or not
    set_execution_status(job_folders[1], "running")
    checks = [
        ("running", 2, "running"),  # recent progress
        ("running", 20, "lost"),  # no event for 20 min
        ("initializing", 20, "running"),  # long initialization
        ("initializing", 90, "lost"),
        ("completed", 90, "lost"),  # outputs written for 90 min?
    ]
    ok3 = True
    for progress_status, minutes, expected in checks:
        write_old_progress(job_folders[1], progress_status, minutes)
        statuses, status = execution_statuses(campaign_dir)
        print(
            f"Job 2 progress '{progress_status}' {minutes} min ago: {statuses[1]} "
            f"(expected {expected})"
        )
        ok3 = ok3 and statuses[1] == expected
    is_ok = utility.print_test(ok3, "3. lost jobs (no news)") and is_ok

    # 4. run again: the lost job is submitted, not the completed one, the
    # submitted one is refused (still waiting in the queue)
    ok4 = False
    try:
        jobs_run(campaign_dir, backend="slurm", backend_options=backend_options)
    except Exception as e:
        print(f"Run again with a submitted job: refused ({e})")
        ok4 = "job0003" in str(e) and "job0002" not in str(e)
    set_execution_status(job_folders[2], "failed")
    result = jobs_run(campaign_dir, backend="slurm", backend_options=backend_options)
    statuses, status = execution_statuses(campaign_dir)
    print(f"Run again: {result['submitted_jobs']} submitted, {statuses}")
    ok4 = (
        ok4
        and result["submitted_jobs"] == 2
        and statuses == ["completed", "submitted", "submitted"]
    )
    is_ok = utility.print_test(ok4, "4. run again: lost and failed jobs") and is_ok

    # 5. progress: job 2 running for 10 min, half done -> ends in ~10 min
    path = job_folders[1] / JOB_EXECUTION_STATUS_FILENAME
    with open(path) as f:
        data = json.load(f)
    data["status"] = "running"
    data["started_at"] = (datetime.now() - timedelta(minutes=10)).isoformat()
    with open(path, "w") as f:
        json.dump(data, f)
    with open(job_folders[1] / JOB_PROGRESS_FILENAME, "w") as f:
        json.dump(
            {
                "status": "running",
                "generated_events": 500,
                "expected_events": 1000,
                "updated_at": datetime.now().isoformat(),
            },
            f,
        )
    statuses, status = execution_statuses(campaign_dir)
    progress = status["progress"]
    print(f"Progress: {progress}")
    remaining = progress["running_remaining_seconds"]
    is_ok = (
        utility.print_test(
            abs(progress["fraction"] - 0.5) < 1e-6  # (1 + 0.5 + 0) / 3
            and progress["number_of_completed_durations"] == 1
            and remaining is not None
            and abs(remaining - 600) < 10
            and progress["not_started"] == 1,
            "5. progress: fraction of the events, end of the running jobs",
        )
        and is_ok
    )

    # 6. output folder of a moved campaign, default number of workers
    ok6 = True
    for folder, expected_error in [
        ("/nonexistent_lustre_folder/output", True),
        (paths.output / "new_folder" / "merged", False),
    ]:
        try:
            _check_merge_output_dir(folder)
            error = False
        except GateMergeError as e:
            print(f"Merge output {folder}: {e}")
            error = True
        ok6 = ok6 and error == expected_error
    manifest_path, manifest = _load_jobs_manifest(campaign_dir)
    manifest["number_of_jobs"] = 10000
    n = _get_default_number_of_workers(manifest_path, manifest)
    print(f"Default workers for 10000 jobs: {n} ({os.cpu_count()} cores)")
    ok6 = ok6 and 1 <= n <= os.cpu_count()
    is_ok = (
        utility.print_test(ok6, "6. merge output folder, number of workers") and is_ok
    )

    # 7. cancel. slurm: the ids given to the fake scancel
    fake_scancel = paths.output / "fake_scancel.sh"
    scancel_args = paths.output / "scancel_args.txt"
    fake_scancel.write_text(f'#!/bin/sh\necho "$@" > {scancel_args}\n')
    os.chmod(fake_scancel, 0o755)
    for job_folder, status in (
        (job_folders[1], "running"),
        (job_folders[2], "submitted"),
    ):
        path = job_folder / JOB_EXECUTION_STATUS_FILENAME
        with open(path) as f:
            data = json.load(f)
        data.update({"status": status, "backend": "slurm", "scheduler_job_id": "4242"})
        with open(path, "w") as f:
            json.dump(data, f)
    write_old_progress(job_folders[1], "running", 0)
    result = jobs_cancel(
        campaign_dir, backend_options={"cancel_binary": str(fake_scancel)}
    )
    statuses, _ = execution_statuses(campaign_dir)
    print(f"Cancel (slurm): {result}, {statuses}")
    ok7 = (
        result["cancelled_jobs"] == ["job0002", "job0003"]
        and scancel_args.read_text().split() == ["4242", "4242"]
        and statuses == ["completed", "cancelled", "cancelled"]
    )

    # local: a running job (a sleeping process) is stopped
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    path = job_folders[1] / JOB_EXECUTION_STATUS_FILENAME
    with open(path) as f:
        data = json.load(f)
    data.update(
        {
            "status": "running",
            "backend": "local_pool",
            "pid": process.pid,
            "hostname": socket.gethostname(),
        }
    )
    with open(path, "w") as f:
        json.dump(data, f)
    write_old_progress(job_folders[1], "running", 0)
    result = jobs_cancel(campaign_dir)
    try:
        process.wait(timeout=20)
        stopped = True
    except subprocess.TimeoutExpired:
        process.kill()
        stopped = False
    statuses, status = execution_statuses(campaign_dir)
    print(f"Cancel (local): {result}, process stopped: {stopped}, {statuses}")
    ok7 = (
        ok7
        and stopped
        and result["cancelled_jobs"] == ["job0002"]
        and statuses[1] == "cancelled"
        and status["execution_counts"]["cancelled"] == 2
    )

    # the cancelled jobs are run again
    result = jobs_run(campaign_dir, backend="slurm", backend_options=backend_options)
    statuses, _ = execution_statuses(campaign_dir)
    print(f"Run again: {result['submitted_jobs']} submitted, {statuses}")
    ok7 = ok7 and result["submitted_jobs"] == 2 and statuses[0] == "completed"
    is_ok = utility.print_test(ok7, "7. cancel (slurm, local), run again") and is_ok

    utility.test_ok(is_ok)

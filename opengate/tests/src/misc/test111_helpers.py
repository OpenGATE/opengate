#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import uuid
from pathlib import Path

import opengate as gate
from opengate.jobs import (
    JOB_EXECUTION_STATUS_FILENAME,
    JOBS_BACKEND_STATUS_FILENAME,
    JOBS_MANIFEST_FILENAME,
)
from opengate.serialization import dump_json, load_json, load_json_with_retry


def build_simple_simulation(output_path):
    sim = gate.Simulation()
    sim.output_dir = output_path
    sim.visu = False

    box = sim.add_volume("Box", "box")
    box.size = [10.0, 10.0, 10.0]

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.number_of_primaries = [20, 30]
    source.direction.type = "iso"
    source.energy.mono = 1.0 * gate.g4_units.MeV

    sim.run_timing_intervals = [[0.0, 1.0], [1.0, 2.0]]
    return sim


def load_manifest(split_root):
    with open(Path(split_root) / JOBS_MANIFEST_FILENAME, "r") as input_file:
        return load_json(input_file)


def load_execution_status(job_folder):
    status_path = Path(job_folder) / JOB_EXECUTION_STATUS_FILENAME
    if not status_path.exists():
        return None
    return load_json_with_retry(status_path)


def load_backend_status(split_root):
    status_path = Path(split_root) / JOBS_BACKEND_STATUS_FILENAME
    if not status_path.exists():
        return None
    return load_json_with_retry(status_path)


def write_execution_status(job_folder, status_data):
    status_path = Path(job_folder) / JOB_EXECUTION_STATUS_FILENAME
    temporary_status_path = status_path.with_name(
        f".{status_path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with open(temporary_status_path, "w") as output_file:
            dump_json(status_data, output_file)
            output_file.flush()
            os.fsync(output_file.fileno())
        os.replace(temporary_status_path, status_path)
    finally:
        if temporary_status_path.exists():
            temporary_status_path.unlink()


def _format_execution_status_snapshot(split_root, manifest):
    job_snapshots = []
    for job in manifest["jobs"]:
        job_folder = Path(split_root) / job["folder_name"]
        status = load_execution_status(job_folder)
        if status is None:
            job_snapshots.append(f"{job['folder_name']}: <missing>")
            continue
        job_snapshots.append(
            (
                f"{job['folder_name']}: "
                f"status={status.get('status')} "
                f"submitted_at={status.get('submitted_at')} "
                f"started_at={status.get('started_at')} "
                f"finished_at={status.get('finished_at')} "
                f"updated_at={status.get('updated_at')}"
            )
        )

    backend_status = load_backend_status(split_root)
    if backend_status is None:
        backend_snapshot = "<missing>"
    else:
        backend_snapshot = (
            f"backend={backend_status.get('backend')} "
            f"status={backend_status.get('status')} "
            f"submitted_jobs={backend_status.get('submitted_jobs')} "
            f"skipped_completed_jobs={backend_status.get('skipped_completed_jobs')} "
            f"campaign_process_pid={backend_status.get('campaign_process_pid')} "
            f"updated_at={backend_status.get('updated_at')}"
        )

    return job_snapshots, backend_snapshot


def _print_execution_status_snapshot(split_root, manifest, header):
    job_snapshots, backend_snapshot = _format_execution_status_snapshot(
        split_root, manifest
    )
    print(header)
    print(f"  Backend status: {backend_snapshot}")
    for job_snapshot in job_snapshots:
        print(f"  {job_snapshot}")
    return job_snapshots, backend_snapshot


def wait_until_execution_status(
    split_root, expected_status, expected_count, timeout=60
):
    manifest = load_manifest(split_root)
    deadline = time.time() + timeout
    statuses = []
    while time.time() < deadline:
        statuses = []
        for job in manifest["jobs"]:
            job_folder = Path(split_root) / job["folder_name"]
            status = load_execution_status(job_folder)
            if status is not None:
                statuses.append(status.get("status"))
        if statuses.count(expected_status) == expected_count:
            _print_execution_status_snapshot(
                split_root,
                manifest,
                (
                    f"Execution status reached '{expected_status}' for "
                    f"{expected_count} job(s):"
                ),
            )
            return statuses
        time.sleep(0.5)
    job_snapshots, backend_snapshot = _print_execution_status_snapshot(
        split_root,
        manifest,
        (
            f"Execution status timed out while waiting for "
            f"'{expected_status}' on {expected_count} job(s):"
        ),
    )
    raise RuntimeError(
        f"Timed out waiting for {expected_count} jobs to reach status '{expected_status}'. "
        f"Observed statuses: {statuses}. "
        f"Backend status: {backend_snapshot}. "
        f"Per-job snapshots: {job_snapshots}"
    )


def wait_until_execution_counts(split_root, expected_counts, timeout=60):
    manifest = load_manifest(split_root)
    deadline = time.time() + timeout
    statuses = []
    while time.time() < deadline:
        statuses = []
        for job in manifest["jobs"]:
            job_folder = Path(split_root) / job["folder_name"]
            status = load_execution_status(job_folder)
            if status is not None:
                statuses.append(status.get("status"))
        counts_ok = True
        for status_name, expected_count in expected_counts.items():
            if statuses.count(status_name) != expected_count:
                counts_ok = False
                break
        if counts_ok:
            _print_execution_status_snapshot(
                split_root,
                manifest,
                f"Execution counts reached {expected_counts}:",
            )
            return statuses
        time.sleep(0.5)
    job_snapshots, backend_snapshot = _print_execution_status_snapshot(
        split_root,
        manifest,
        f"Execution counts timed out while waiting for {expected_counts}:",
    )
    raise RuntimeError(
        f"Timed out waiting for execution counts {expected_counts}. "
        f"Observed statuses: {statuses}. "
        f"Backend status: {backend_snapshot}. "
        f"Per-job snapshots: {job_snapshots}"
    )

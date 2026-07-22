#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from pathlib import Path

import opengate as gate
from opengate.jobs import (
    JOB_EXECUTION_STATUS_FILENAME,
    JOBS_BACKEND_STATUS_FILENAME,
    JOBS_MANIFEST_FILENAME,
)
from opengate.serialization import dump_json, load_json


def build_simple_simulation(output_path):
    sim = gate.Simulation()
    sim.output_dir = output_path
    sim.visu = False

    box = sim.add_volume("Box", "box")
    box.size = [10.0, 10.0, 10.0]

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.n = [20, 30]
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
    with open(status_path, "r") as input_file:
        return load_json(input_file)


def load_backend_status(split_root):
    status_path = Path(split_root) / JOBS_BACKEND_STATUS_FILENAME
    if not status_path.exists():
        return None
    with open(status_path, "r") as input_file:
        return load_json(input_file)


def write_execution_status(job_folder, status_data):
    with open(Path(job_folder) / JOB_EXECUTION_STATUS_FILENAME, "w") as output_file:
        dump_json(status_data, output_file)


def wait_until_execution_status(
    split_root, expected_status, expected_count, timeout=60
):
    manifest = load_manifest(split_root)
    deadline = time.time() + timeout
    while time.time() < deadline:
        statuses = []
        for job in manifest["jobs"]:
            job_folder = Path(split_root) / job["folder_name"]
            status = load_execution_status(job_folder)
            if status is not None:
                statuses.append(status.get("status"))
        if statuses.count(expected_status) == expected_count:
            return statuses
        time.sleep(0.5)
    raise RuntimeError(
        f"Timed out waiting for {expected_count} jobs to reach status '{expected_status}'. "
        f"Observed statuses: {statuses}"
    )

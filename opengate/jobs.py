import math
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
import json

import numpy as np
import opengate_core as g4

from .exception import GateJobsBackendError, GateMergeError, fatal
from .runtiming import assert_run_timing
from .serialization import dump_json, load_json

JOBS_MANIFEST_FILENAME = "jobs_manifest.json"
JOBS_BACKEND_STATUS_FILENAME = "jobs_backend_status.json"
JOB_METADATA_FILENAME = "job_metadata.json"
JOB_EXECUTION_STATUS_FILENAME = "job_execution_status.json"
JOB_SIMULATION_FILENAME = "simulation.json"
MASTER_SIMULATION_FILENAME = "simulation.json"
JOB_EXECUTION_ALLOWED_STATUSES = ("running", "completed", "failed", "skipped")
HTCONDOR_SUBMIT_FILENAME = "htcondor_jobs.submit"
SLURM_SUBMIT_FILENAME = "slurm_jobs.sh"
SLURM_JOB_FOLDERS_FILENAME = "slurm_job_folders.txt"


def _clone_simulation(simulation):
    # Clone through the JSON serializer so the child jobs are built from the same
    # persisted representation that later jobs_run()/jobs_merge() will use.
    cloned_simulation = type(simulation)()
    cloned_simulation.from_json_string(simulation.to_json_string())
    return cloned_simulation


def _resolve_split_folder(split_path, overwrite_existing_split_folder=False):
    if split_path is None or split_path == "auto":
        timestamp = datetime.now().strftime("jobs_%Y%m%d_%H%M%S")
        split_folder = Path(timestamp)
        suffix = 1
        while split_folder.exists():
            split_folder = Path(f"{timestamp}_{suffix:02d}")
            suffix += 1
    else:
        split_folder = Path(split_path)
        if split_folder.exists():
            if overwrite_existing_split_folder is False:
                fatal(
                    f"Split path already exists: {split_folder}. "
                    "Please provide a fresh split_path, use split_path=None/'auto', "
                    "or set overwrite_existing_split_folder=True."
                )
            if split_folder.is_dir() is False:
                fatal(
                    f"Cannot overwrite split path {split_folder} because it is not a directory."
                )
            shutil.rmtree(split_folder)
    split_folder.mkdir(parents=True, exist_ok=False)
    return split_folder.resolve()


def _copy_run_timing_intervals(run_timing_intervals):
    return [[interval[0], interval[1]] for interval in run_timing_intervals]


def _create_job_definition(job_index, run_timing_intervals, original_run_indices):
    if len(run_timing_intervals) != len(original_run_indices):
        fatal(
            "Inconsistent split definition: "
            "run_timing_intervals and original_run_indices must have the same length."
        )
    assert_run_timing(run_timing_intervals)
    return {
        "job_index": job_index,
        "folder_name": f"job{job_index:04d}",
        "job_id": uuid.uuid4().hex,
        # Local run timing intervals of this job, in the child's own run ordering.
        "run_timing_intervals": run_timing_intervals,
        # For each local run, store which original master run it comes from.
        "original_run_indices": list(original_run_indices),
    }


def _split_in_time_per_run(run_timing_intervals, number_of_jobs):
    if number_of_jobs % len(run_timing_intervals) != 0:
        fatal(
            "The split_in_time_per_run policy requires the number of jobs to be a multiple "
            f"of the number of run timing intervals. Received {number_of_jobs} jobs "
            f"for {len(run_timing_intervals)} timing intervals."
        )

    jobs_per_interval = number_of_jobs // len(run_timing_intervals)
    job_definitions = []
    job_index = 1
    for original_run_index, interval in enumerate(run_timing_intervals):
        start_time, end_time = interval
        duration = end_time - start_time
        step = duration / jobs_per_interval
        current_start = start_time
        for _ in range(jobs_per_interval):
            current_end = current_start + step
            job_definitions.append(
                _create_job_definition(
                    job_index,
                    [[current_start, current_end]],
                    [original_run_index],
                )
            )
            current_start = current_end
            job_index += 1
    return job_definitions


def _split_in_time_total(run_timing_intervals, number_of_jobs):
    # Split the total active simulation time into consecutive jobs. Unlike
    # _split_in_time_per_run(), a single job may span several original runs.
    total_active_time = sum(end - start for start, end in run_timing_intervals)
    target_job_active_duration = total_active_time / number_of_jobs
    job_definitions = []

    current_original_run_index = 0
    current_time_in_original_run = run_timing_intervals[0][0]
    tolerance = max(1e-12, abs(total_active_time) * 1e-12)

    for job_index in range(1, number_of_jobs + 1):
        job_run_timing_intervals = []
        job_original_run_indices = []
        if job_index == number_of_jobs:
            remaining_active_time_to_fill_job = math.inf
        else:
            remaining_active_time_to_fill_job = target_job_active_duration

        while current_original_run_index < len(run_timing_intervals):
            original_run_start, original_run_end = run_timing_intervals[
                current_original_run_index
            ]
            if current_time_in_original_run < original_run_start:
                current_time_in_original_run = original_run_start

            active_time_still_available_in_original_run = (
                original_run_end - current_time_in_original_run
            )
            if active_time_still_available_in_original_run <= tolerance:
                current_original_run_index += 1
                if current_original_run_index < len(run_timing_intervals):
                    current_time_in_original_run = run_timing_intervals[
                        current_original_run_index
                    ][0]
                continue

            if remaining_active_time_to_fill_job is math.inf:
                active_time_to_take_from_original_run = (
                    active_time_still_available_in_original_run
                )
            else:
                active_time_to_take_from_original_run = min(
                    active_time_still_available_in_original_run,
                    remaining_active_time_to_fill_job,
                )

            job_run_timing_intervals.append(
                [
                    current_time_in_original_run,
                    current_time_in_original_run
                    + active_time_to_take_from_original_run,
                ]
            )
            job_original_run_indices.append(current_original_run_index)
            current_time_in_original_run += active_time_to_take_from_original_run

            if remaining_active_time_to_fill_job is not math.inf:
                remaining_active_time_to_fill_job -= (
                    active_time_to_take_from_original_run
                )
                if remaining_active_time_to_fill_job <= tolerance:
                    break

            if original_run_end - current_time_in_original_run <= tolerance:
                current_original_run_index += 1
                if current_original_run_index < len(run_timing_intervals):
                    current_time_in_original_run = run_timing_intervals[
                        current_original_run_index
                    ][0]

        if len(job_run_timing_intervals) == 0:
            fatal(
                f"Unable to build split_in_time_total job {job_index}. "
                "This indicates an internal splitting error."
            )

        job_definitions.append(
            _create_job_definition(
                job_index, job_run_timing_intervals, job_original_run_indices
            )
        )

    return job_definitions


def _generate_job_definitions(run_timing_intervals, number_of_jobs, policy):
    if number_of_jobs < 1:
        fatal(f"The number of jobs must be >= 1, but received {number_of_jobs}.")
    if policy == "split_in_time_per_run":
        return _split_in_time_per_run(run_timing_intervals, number_of_jobs)
    if policy == "split_in_time_total":
        return _split_in_time_total(run_timing_intervals, number_of_jobs)
    fatal(
        f"Unknown split policy '{policy}'. "
        "Known policies are: 'split_in_time_per_run', 'split_in_time_total'."
    )


def _compute_source_n_assignments(
    simulation, original_run_timing_intervals, job_definitions
):
    # Keep the child simulations self-consistent for later execution by rewriting
    # per-run source.n arrays to the local runs of each job.
    source_n_assignments = {
        job_definition["job_index"]: {} for job_definition in job_definitions
    }
    job_segments_by_original_run_index = {
        run_index: [] for run_index in range(len(original_run_timing_intervals))
    }
    for job_definition in job_definitions:
        for local_run_index, original_run_index in enumerate(
            job_definition["original_run_indices"]
        ):
            local_interval = job_definition["run_timing_intervals"][local_run_index]
            duration = local_interval[1] - local_interval[0]
            job_segments_by_original_run_index[original_run_index].append(
                {
                    "job_index": job_definition["job_index"],
                    "local_run_index": local_run_index,
                    "duration": duration,
                }
            )

    for source in simulation.source_manager.sources.values():
        if source.activity > 0:
            continue

        counts = np.asarray(source.n, dtype=int)
        if len(counts.shape) == 0:
            counts = np.asarray([int(counts)], dtype=int)
        if len(counts) != len(original_run_timing_intervals):
            fatal(
                f"Source '{source.name}' defines n={list(counts)}, but the simulation has "
                f"{len(original_run_timing_intervals)} run timing intervals."
            )

        assignments_by_job = {
            job_definition["job_index"]: [0]
            * len(job_definition["run_timing_intervals"])
            for job_definition in job_definitions
        }

        for original_run_index, count in enumerate(counts):
            contributing_job_segments = job_segments_by_original_run_index[
                original_run_index
            ]
            if len(contributing_job_segments) == 0:
                continue
            total_split_duration_for_original_run = sum(
                segment["duration"] for segment in contributing_job_segments
            )
            if total_split_duration_for_original_run <= 0:
                allocated_counts = [0] * len(contributing_job_segments)
            else:
                # Distribute integer counts proportionally to the fraction of the
                # original run duration assigned to each child segment.
                exact_counts = [
                    count * segment["duration"] / total_split_duration_for_original_run
                    for segment in contributing_job_segments
                ]
                allocated_counts = [int(math.floor(value)) for value in exact_counts]
                remainder = int(count - sum(allocated_counts))
                ranking = sorted(
                    range(len(contributing_job_segments)),
                    key=lambda i: (-(exact_counts[i] - allocated_counts[i]), i),
                )
                for i in ranking[:remainder]:
                    allocated_counts[i] += 1

            for segment, allocated_count in zip(
                contributing_job_segments, allocated_counts
            ):
                assignments_by_job[segment["job_index"]][
                    segment["local_run_index"]
                ] = allocated_count

        for job_index, assigned_counts in assignments_by_job.items():
            source_n_assignments[job_index][source.name] = assigned_counts

    return source_n_assignments


def _configure_child_simulation(
    child_simulation,
    job_definition,
    source_n_assignments,
    parent_simulation_id,
    split_root_folder,
):
    job_folder = split_root_folder / job_definition["folder_name"]
    child_simulation.output_dir = job_folder
    child_simulation.run_timing_intervals = _copy_run_timing_intervals(
        job_definition["run_timing_intervals"]
    )

    # Dynamic objects are defined against the master run ordering. Rewrite them
    # to the local run ordering of this child simulation.
    for volume in child_simulation.volume_manager.dynamic_volumes:
        volume.reassign_dynamic_params_for_run_indices(
            job_definition["original_run_indices"]
        )
    for source in child_simulation.source_manager.dynamic_sources:
        source.reassign_dynamic_params_for_run_indices(
            job_definition["original_run_indices"]
        )

    # Rewrite source.n to match the child's local runs so the serialized child is
    # directly executable later without extra split-time logic.
    for source_name, assigned_counts in source_n_assignments.items():
        child_source = child_simulation.source_manager.get_source(source_name)
        child_source.n = assigned_counts

    child_metadata = {
        "job_id": job_definition["job_id"],
        "job_index": job_definition["job_index"],
        "parent_simulation_id": parent_simulation_id,
        "run_timing_intervals": _copy_run_timing_intervals(
            job_definition["run_timing_intervals"]
        ),
        "original_run_indices": list(job_definition["original_run_indices"]),
        "simulation_filename": JOB_SIMULATION_FILENAME,
    }
    return job_folder, child_metadata


def jobs_split(
    simulation,
    number_of_jobs,
    split_path,
    policy="split_in_time_per_run",
    link_files=False,
    overwrite_existing_split_folder=False,
    **options,
):
    # Split authoritative, resolved configuration rather than the raw user
    # inputs so child jobs inherit explicit timing anchors and helper actors.
    simulation.resolve_and_validate_config(context="split_preparation")

    original_run_timing_intervals = _copy_run_timing_intervals(
        simulation.run_timing_intervals
    )

    # Build the split plan before touching the filesystem so invalid requests do
    # not leave behind half-created split folders.
    job_definitions = _generate_job_definitions(
        original_run_timing_intervals, number_of_jobs, policy
    )
    source_n_assignments = _compute_source_n_assignments(
        simulation, original_run_timing_intervals, job_definitions
    )
    split_root_folder = _resolve_split_folder(
        split_path,
        overwrite_existing_split_folder=overwrite_existing_split_folder,
    )
    simulation_id = uuid.uuid4().hex
    created_at = datetime.now().isoformat()

    simulation.to_json_file(
        directory=split_root_folder,
        filename=Path(MASTER_SIMULATION_FILENAME),
    )
    simulation.archive_input_files(directory=split_root_folder, link_files=link_files)

    jobs_manifest = {
        "simulation_id": simulation_id,
        "created_at": created_at,
        "policy": policy,
        "options": options,
        "number_of_jobs": number_of_jobs,
        "original_run_timing_intervals": original_run_timing_intervals,
        "master_simulation_filename": MASTER_SIMULATION_FILENAME,
        "jobs": [],
    }

    for job_definition in job_definitions:
        # Each child simulation is materialized from the master serializer and
        # then rewritten to the local timing structure of exactly one job.
        child_simulation = _clone_simulation(simulation)
        job_folder, child_metadata = _configure_child_simulation(
            child_simulation,
            job_definition,
            source_n_assignments[job_definition["job_index"]],
            simulation_id,
            split_root_folder,
        )
        job_folder.mkdir(parents=True, exist_ok=False)
        child_simulation_dict = child_simulation.to_dictionary()
        updated_child_simulation_dict = child_simulation.archive_input_files(
            directory=job_folder,
            dct=child_simulation_dict,
            link_files=link_files,
            update_input_paths_in_dict=True,
        )
        with open(job_folder / JOB_SIMULATION_FILENAME, "w") as output_file:
            dump_json(updated_child_simulation_dict, output_file)
        with open(job_folder / JOB_METADATA_FILENAME, "w") as output_file:
            dump_json(child_metadata, output_file)
        jobs_manifest["jobs"].append(
            {
                "job_index": job_definition["job_index"],
                "job_id": child_metadata["job_id"],
                "folder_name": job_definition["folder_name"],
                "metadata_filename": JOB_METADATA_FILENAME,
            }
        )

    with open(split_root_folder / JOBS_MANIFEST_FILENAME, "w") as output_file:
        dump_json(jobs_manifest, output_file)

    return split_root_folder


def _now_isoformat():
    return datetime.now().isoformat()


def _get_platform_process_start_method():
    if sys.platform == "darwin" or os.name == "nt":
        return "spawn"
    return "fork"


def _get_job_execution_status_path(job_folder):
    return Path(job_folder) / JOB_EXECUTION_STATUS_FILENAME


def _dump_json_atomic(output_path, data):
    """Write JSON atomically so status readers never observe a truncated file."""
    output_path = Path(output_path)
    temporary_output_path = output_path.with_name(
        f".{output_path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with open(temporary_output_path, "w") as output_file:
            dump_json(data, output_file)
            output_file.flush()
            os.fsync(output_file.fileno())
        os.replace(temporary_output_path, output_path)
    finally:
        if temporary_output_path.exists():
            temporary_output_path.unlink()


def _load_job_metadata(job_folder):
    with open(Path(job_folder) / JOB_METADATA_FILENAME, "r") as input_file:
        return load_json(input_file)


def _load_jobs_manifest(manifest_or_dir_path):
    path = Path(manifest_or_dir_path).resolve()
    manifest_path = path / JOBS_MANIFEST_FILENAME if path.is_dir() else path
    if not manifest_path.exists():
        fatal(f"Jobs manifest file not found at '{manifest_path}'.")
    with open(manifest_path, "r") as input_file:
        manifest = load_json(input_file)
    return manifest_path, manifest


def _format_timing_interval(interval):
    start_str = str(g4.G4BestUnit(interval[0], "Time")).strip()
    end_str = str(g4.G4BestUnit(interval[1], "Time")).strip()
    return f"[{start_str}, {end_str}]"


def _format_timing_intervals(intervals):
    return ", ".join(_format_timing_interval(interval) for interval in intervals)


def _format_original_run_indices(original_run_indices):
    if len(original_run_indices) == 0:
        return "[]"
    unique_indices = []
    for run_index in original_run_indices:
        if run_index not in unique_indices:
            unique_indices.append(run_index)
    return "[" + ", ".join(str(run_index) for run_index in unique_indices) + "]"


def format_jobs_split_summary(manifest_or_dir_path):
    manifest_path, manifest = _load_jobs_manifest(manifest_or_dir_path)
    split_root_folder = manifest_path.parent
    lines = [
        "Jobs split summary:",
        f"- master folder: {split_root_folder}",
        f"| simulation: {split_root_folder / manifest.get('master_simulation_filename', MASTER_SIMULATION_FILENAME)}",
        f"| simulation id: {manifest.get('simulation_id', 'Unknown')}",
        f"| split policy: {manifest.get('policy', 'Unknown')}",
        f"| original run timing intervals: {_format_timing_intervals(manifest.get('original_run_timing_intervals', []))}",
        "| jobs:",
    ]
    for job_item in manifest.get("jobs", []):
        job_folder = split_root_folder / job_item["folder_name"]
        metadata = _load_job_metadata(job_folder)
        lines.extend(
            [
                f"| - {job_item['folder_name']}",
                f"|   | folder: {job_folder}",
                f"|   | original runs: {_format_original_run_indices(metadata.get('original_run_indices', []))}",
                f"|   | local timing intervals: {_format_timing_intervals(metadata.get('run_timing_intervals', []))}",
            ]
        )
    return "\n".join(lines)


def print_jobs_split_summary(manifest_or_dir_path):
    summary = format_jobs_split_summary(manifest_or_dir_path)
    print(summary)
    return summary


def _get_jobs_backend_status_path(split_root_folder):
    return Path(split_root_folder) / JOBS_BACKEND_STATUS_FILENAME


def load_jobs_backend_status(split_root_folder):
    status_path = _get_jobs_backend_status_path(split_root_folder)
    if not status_path.exists():
        return None
    with open(status_path, "r") as input_file:
        return load_json(input_file)


def _write_jobs_backend_status(
    split_root_folder,
    backend,
    status,
    submitted_jobs,
    skipped_completed_jobs,
    submitted_at=None,
    campaign_process_pid=None,
    scheduler_job_id=None,
    submit_file_path=None,
    submit_command=None,
    submission_stdout=None,
    submission_stderr=None,
):
    status_data = {
        "backend": backend,
        "status": status,
        "submitted_jobs": submitted_jobs,
        "skipped_completed_jobs": skipped_completed_jobs,
        "submitted_at": submitted_at,
        "updated_at": _now_isoformat(),
        "campaign_process_pid": campaign_process_pid,
        "scheduler_job_id": scheduler_job_id,
        "submit_file_path": submit_file_path,
        "submit_command": submit_command,
        "submission_stdout": submission_stdout,
        "submission_stderr": submission_stderr,
    }
    _dump_json_atomic(_get_jobs_backend_status_path(split_root_folder), status_data)
    return status_data


def load_job_execution_status(job_folder):
    status_path = _get_job_execution_status_path(job_folder)
    if not status_path.exists():
        return None
    with open(status_path, "r") as input_file:
        return load_json(input_file)


def _write_job_execution_status(
    job_folder,
    metadata,
    backend,
    status,
    submitted_at=None,
    started_at=None,
    finished_at=None,
    error_message=None,
):
    if status not in JOB_EXECUTION_ALLOWED_STATUSES:
        fatal(
            f"Unknown execution status '{status}'. "
            f"Allowed values are {JOB_EXECUTION_ALLOWED_STATUSES}."
        )
    status_data = {
        "job_id": metadata.get("job_id"),
        "job_index": metadata.get("job_index"),
        "backend": backend,
        "status": status,
        "submitted_at": submitted_at,
        "started_at": started_at,
        "finished_at": finished_at,
        "updated_at": _now_isoformat(),
        "error_message": error_message,
    }
    _dump_json_atomic(_get_job_execution_status_path(job_folder), status_data)
    return status_data


def _run_job_folder(job_folder, backend, start_new_process):
    """Execute one child job from its persisted job folder.

    The caller decides whether the simulation itself should run in the current
    process or dispatch one more subprocess via
    ``sim.run(start_new_process=...)``. That choice is separate from the
    campaign-level process created in ``jobs_run()``, whose role is only to
    detach orchestration from the caller.
    """
    job_folder = Path(job_folder).resolve()
    metadata = {
        "job_id": None,
        "job_index": None,
    }
    submitted_at = _now_isoformat()
    started_at = _now_isoformat()

    try:
        metadata = _load_job_metadata(job_folder)
        _write_job_execution_status(
            job_folder,
            metadata,
            backend=backend,
            status="running",
            submitted_at=submitted_at,
            started_at=started_at,
        )

        simulation_path = job_folder / metadata.get(
            "simulation_filename", JOB_SIMULATION_FILENAME
        )
        sim = create_sim_from_json(simulation_path)
        sim.output_dir = job_folder
        sim.run(start_new_process=start_new_process)

        finished_at = _now_isoformat()
        _write_job_execution_status(
            job_folder,
            metadata,
            backend=backend,
            status="completed",
            submitted_at=submitted_at,
            started_at=started_at,
            finished_at=finished_at,
        )
        return {
            "job_id": metadata.get("job_id"),
            "job_index": metadata.get("job_index"),
            "job_folder": str(job_folder),
            "status": "completed",
        }
    except Exception as error:
        finished_at = _now_isoformat()
        error_message = f"{type(error).__name__}: {error}"
        traceback_str = traceback.format_exc()
        _write_job_execution_status(
            job_folder,
            metadata,
            backend=backend,
            status="failed",
            submitted_at=submitted_at,
            started_at=started_at,
            finished_at=finished_at,
            error_message=f"{error_message}\n{traceback_str}",
        )
        return {
            "job_id": metadata.get("job_id"),
            "job_index": metadata.get("job_index"),
            "job_folder": str(job_folder),
            "status": "failed",
            "error_message": error_message,
        }


def _run_job_folder_cli(job_folder, backend="local_cli", start_new_process=False):
    """Run one persisted child job folder and return its execution summary."""
    return _run_job_folder(
        job_folder,
        backend=backend,
        start_new_process=start_new_process,
    )


def _run_job_folder_local_pool(job_folder):
    # The pool worker process is already the dedicated execution process for this
    # job. Avoid dispatching another subprocess from inside the worker.
    # With maxtasksperchild=1, one pool worker process handles one child job.
    return _run_job_folder(job_folder, backend="local_pool", start_new_process=False)


def _run_job_folders_in_local_sequential(job_folders):
    return [
        # A single sequential campaign process executes jobs one after another, so
        # each child simulation must run in its own subprocess to avoid reusing
        # Geant4 state across jobs. Here, the orchestration process survives across
        # several jobs, but the simulation process does not.
        _run_job_folder(
            job_folder,
            backend="local_sequential",
            start_new_process=True,
        )
        for job_folder in job_folders
    ]


def _run_job_folders_in_local_pool(
    job_folders,
    n_workers,
    start_method="spawn",
    maxtasksperchild=1,
):
    # NOTE: local_pool is a convenience backend, not the most crash-resilient
    # local dispatcher. If a worker suffers a hard crash such as a C++ segfault,
    # multiprocessing.Pool may propagate an exception to the parent, but in some
    # failure modes it can also become wedged without a clean Python exception.
    # For stronger isolation and more reliable crash detection, a future local
    # backend could dispatch one OS subprocess per job and monitor exit codes,
    # similar in spirit to scheduler-based backends and to local_sequential.
    # Another option would be a more defensive pool orchestration based on
    # apply_async()/timeouts/health checks rather than a single blocking map().
    if int(n_workers) < 1:
        raise GateJobsBackendError("The local_pool backend requires n_workers >= 1.")
    if int(maxtasksperchild) != 1:
        raise GateJobsBackendError(
            "The local_pool backend currently requires maxtasksperchild=1 so each "
            "worker process executes at most one job."
        )
    ctx = multiprocessing.get_context(start_method)
    pool = ctx.Pool(
        processes=int(n_workers),
        maxtasksperchild=maxtasksperchild,
    )
    try:
        results = pool.map(_run_job_folder_local_pool, [str(p) for p in job_folders])
        # Shut the pool down gracefully once all jobs completed. Using the Pool
        # context manager would terminate workers on exit, which is too abrupt
        # here and can trigger resource-tracker warnings on shutdown.
        pool.close()
        pool.join()
        return results
    except Exception:
        pool.terminate()
        pool.join()
        raise


def _render_htcondor_submit_file_lines(job_folders, backend_options):
    submit_file_commands = {
        "universe": "vanilla",
        "executable": backend_options["job_runner_command"],
        "arguments": ". --backend htcondor",
        "initialdir": "$(job_folder)",
        "output": "opengate_job_runner.stdout",
        "error": "opengate_job_runner.stderr",
        "log": "opengate_job_runner.condor.log",
        "getenv": "True",
    }
    submit_file_commands.update(backend_options.get("submit_file_commands", {}))

    lines = [f"{key} = {value}" for key, value in submit_file_commands.items()]
    lines.extend(
        [
            "",
            "queue job_folder from (",
            *[str(Path(job_folder).resolve()) for job_folder in job_folders],
            ")",
            "",
        ]
    )
    return lines


def _write_htcondor_submit_file(split_root_folder, job_folders, backend_options):
    submit_file_path = Path(split_root_folder) / backend_options["submit_filename"]
    submit_file_path.parent.mkdir(parents=True, exist_ok=True)
    submit_file_content = "\n".join(
        _render_htcondor_submit_file_lines(job_folders, backend_options)
    )
    with open(submit_file_path, "w") as output_file:
        output_file.write(submit_file_content)
    return submit_file_path


def _extract_htcondor_cluster_id(submit_stdout):
    match = re.search(r"cluster\s+(\d+)", submit_stdout, flags=re.IGNORECASE)
    if match is None:
        return None
    return match.group(1)


def _write_slurm_job_folders_file(split_root_folder, job_folders, backend_options):
    job_folders_path = Path(split_root_folder) / backend_options["job_folders_filename"]
    job_folders_path.parent.mkdir(parents=True, exist_ok=True)
    with open(job_folders_path, "w") as output_file:
        for job_folder in job_folders:
            output_file.write(f"{Path(job_folder).resolve()}\n")
    return job_folders_path


def _example_render_slurm_submit_script_lines(job_folders_file_path, **kwargs):
    """Example Slurm submit-script renderer for users and tests.

    The public Slurm backend expects the user to provide a renderer via
    backend_options["submit_script_renderer"]. This helper remains as a
    reference template and for internal tests.
    """
    script_commands = {
        "output": "opengate_job_runner.%A_%a.out",
        "error": "opengate_job_runner.%A_%a.err",
    }
    script_commands.update(kwargs.get("script_commands", {}))
    job_runner_command = kwargs.get("job_runner_command", "opengate_job_runner")
    lines = ["#!/bin/sh"]
    lines.extend([f"#SBATCH --{key}={value}" for key, value in script_commands.items()])
    lines.extend(
        [
            "",
            "set -eu",
            f'JOB_FOLDERS_FILE="{job_folders_file_path}"',
            'JOB_FOLDER="$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$JOB_FOLDERS_FILE")"',
            'cd "$JOB_FOLDER"',
            f"exec {job_runner_command} . --backend slurm",
            "",
        ]
    )
    return lines


def _write_slurm_submit_script(
    split_root_folder, job_folders_file_path, backend_options
):
    submit_file_path = Path(split_root_folder) / backend_options["submit_filename"]
    submit_file_path.parent.mkdir(parents=True, exist_ok=True)
    submit_script_lines = backend_options["submit_script_renderer"](
        job_folders_file_path,
        **backend_options.get("submit_script_renderer_kwargs", {}),
    )
    submit_file_content = "\n".join([str(line) for line in submit_script_lines])
    with open(submit_file_path, "w") as output_file:
        output_file.write(submit_file_content)
    os.chmod(submit_file_path, 0o755)
    return submit_file_path


def _extract_slurm_job_id(submit_stdout):
    match = re.search(
        r"Submitted batch job\s+(\d+)", submit_stdout, flags=re.IGNORECASE
    )
    if match is None:
        return None
    return match.group(1)


def _submit_job_folders_to_htcondor(
    split_root_folder,
    job_folders,
    backend_options,
    skipped_completed_jobs,
):
    submit_file_path = _write_htcondor_submit_file(
        split_root_folder, job_folders, backend_options
    )
    command = [backend_options["submit_binary"]]
    command.extend(backend_options.get("command_line_args", []))
    command.append(str(submit_file_path))
    try:
        completed_process = subprocess.run(
            command,
            cwd=split_root_folder,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise GateJobsBackendError(
            f"HTCondor submission command not found: {backend_options['submit_binary']}."
        ) from error

    if completed_process.returncode != 0:
        raise GateJobsBackendError(
            "HTCondor submission failed.\n"
            f"Command: {' '.join(command)}\n"
            f"Return code: {completed_process.returncode}\n"
            f"stdout:\n{completed_process.stdout}\n"
            f"stderr:\n{completed_process.stderr}"
        )

    status_data = _write_jobs_backend_status(
        split_root_folder,
        backend="htcondor",
        status="submitted",
        submitted_jobs=len(job_folders),
        skipped_completed_jobs=skipped_completed_jobs,
        submitted_at=_now_isoformat(),
        scheduler_job_id=_extract_htcondor_cluster_id(completed_process.stdout),
        submit_file_path=str(submit_file_path),
        submit_command=command,
        submission_stdout=completed_process.stdout,
        submission_stderr=completed_process.stderr,
    )

    return {
        "submit_file_path": str(submit_file_path),
        "submission_command": command,
        "submission_stdout": completed_process.stdout,
        "submission_stderr": completed_process.stderr,
        "scheduler_job_id": status_data["scheduler_job_id"],
        "backend_status_path": str(_get_jobs_backend_status_path(split_root_folder)),
    }


def _submit_job_folders_to_slurm(
    split_root_folder,
    job_folders,
    backend_options,
    skipped_completed_jobs,
):
    job_folders_file_path = _write_slurm_job_folders_file(
        split_root_folder, job_folders, backend_options
    )
    submit_file_path = _write_slurm_submit_script(
        split_root_folder, job_folders_file_path, backend_options
    )
    command = [backend_options["submit_binary"]]
    command.extend(backend_options.get("command_line_args", []))
    command.append(f"--array=0-{len(job_folders) - 1}")
    command.append(str(submit_file_path))
    try:
        completed_process = subprocess.run(
            command,
            cwd=split_root_folder,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise GateJobsBackendError(
            f"Slurm submission command not found: {backend_options['submit_binary']}."
        ) from error

    if completed_process.returncode != 0:
        raise GateJobsBackendError(
            "Slurm submission failed.\n"
            f"Command: {' '.join(command)}\n"
            f"Return code: {completed_process.returncode}\n"
            f"stdout:\n{completed_process.stdout}\n"
            f"stderr:\n{completed_process.stderr}"
        )

    status_data = _write_jobs_backend_status(
        split_root_folder,
        backend="slurm",
        status="submitted",
        submitted_jobs=len(job_folders),
        skipped_completed_jobs=skipped_completed_jobs,
        submitted_at=_now_isoformat(),
        scheduler_job_id=_extract_slurm_job_id(completed_process.stdout),
        submit_file_path=str(submit_file_path),
        submit_command=command,
        submission_stdout=completed_process.stdout,
        submission_stderr=completed_process.stderr,
    )

    return {
        "submit_file_path": str(submit_file_path),
        "job_folders_file_path": str(job_folders_file_path),
        "submission_command": command,
        "submission_stdout": completed_process.stdout,
        "submission_stderr": completed_process.stderr,
        "scheduler_job_id": status_data["scheduler_job_id"],
        "backend_status_path": str(_get_jobs_backend_status_path(split_root_folder)),
    }


def _run_jobs_campaign(job_folders, backend, backend_options):
    """Run the detached campaign-level orchestration for a selected backend.

    This function does not represent one simulation run itself. It decides how
    the selected child jobs are executed after ``jobs_run()`` has detached the
    campaign from the caller process.
    """
    if backend == "local_sequential":
        return _run_job_folders_in_local_sequential(job_folders)

    if backend == "local_pool":
        return _run_job_folders_in_local_pool(job_folders, **backend_options)

    raise GateJobsBackendError(f"Unknown jobs backend '{backend}'.")


def _validate_jobs_backend_options(backend, backend_options):
    if backend_options is None:
        backend_options = {}

    if backend == "local_sequential":
        if len(backend_options) > 0:
            raise GateJobsBackendError(
                "The local_sequential backend does not accept backend_options."
            )
        return {}

    if backend == "local_pool":
        pooling_options = dict(backend_options)
        allowed_backend_keys = {"n_workers", "start_method", "maxtasksperchild"}
        unknown_backend_keys = set(pooling_options.keys()).difference(
            allowed_backend_keys
        )
        if len(unknown_backend_keys) > 0:
            raise GateJobsBackendError(
                f"The local_pool backend received unknown backend_options: {sorted(unknown_backend_keys)}."
            )
        if "n_workers" not in pooling_options:
            pooling_options["n_workers"] = os.cpu_count() or 1
        try:
            pooling_options["n_workers"] = int(pooling_options["n_workers"])
        except (TypeError, ValueError) as error:
            raise GateJobsBackendError(
                f"Invalid n_workers value for local_pool: {pooling_options['n_workers']}."
            ) from error
        if pooling_options["n_workers"] < 1:
            raise GateJobsBackendError(
                "The local_pool backend requires n_workers >= 1."
            )
        pooling_options.setdefault("start_method", "spawn")
        try:
            multiprocessing.get_context(pooling_options["start_method"])
        except ValueError as error:
            raise GateJobsBackendError(
                f"Unknown multiprocessing start_method '{pooling_options['start_method']}' "
                "for the local_pool backend."
            ) from error
        pooling_options.setdefault("maxtasksperchild", 1)
        if pooling_options["maxtasksperchild"] is not None:
            try:
                pooling_options["maxtasksperchild"] = int(
                    pooling_options["maxtasksperchild"]
                )
            except (TypeError, ValueError) as error:
                raise GateJobsBackendError(
                    "The local_pool backend requires maxtasksperchild to be "
                    "None or an integer >= 1."
                ) from error
            if pooling_options["maxtasksperchild"] < 1:
                raise GateJobsBackendError(
                    "The local_pool backend requires maxtasksperchild >= 1."
                )
            if pooling_options["maxtasksperchild"] != 1:
                raise GateJobsBackendError(
                    "The local_pool backend currently requires maxtasksperchild=1."
                )
        return pooling_options

    if backend == "htcondor":
        allowed_top_level_keys = {
            "submit_file_commands",
            "command_line_args",
            "job_runner_command",
            "submit_filename",
            "submit_binary",
        }
        unknown_keys = set(backend_options.keys()).difference(allowed_top_level_keys)
        if len(unknown_keys) > 0:
            raise GateJobsBackendError(
                f"The htcondor backend received unknown option groups: {sorted(unknown_keys)}."
            )

        validated_options = dict(backend_options)
        validated_options.setdefault("submit_file_commands", {})
        validated_options.setdefault("command_line_args", [])
        validated_options.setdefault("job_runner_command", "opengate_job_runner")
        validated_options.setdefault("submit_filename", HTCONDOR_SUBMIT_FILENAME)
        validated_options.setdefault("submit_binary", "condor_submit")

        if not isinstance(validated_options["submit_file_commands"], dict):
            raise GateJobsBackendError(
                "The htcondor backend requires submit_file_commands to be a dictionary."
            )
        if not isinstance(validated_options["command_line_args"], (list, tuple)):
            raise GateJobsBackendError(
                "The htcondor backend requires command_line_args to be a list or tuple."
            )

        validated_options["submit_file_commands"] = {
            str(key): str(value)
            for key, value in validated_options["submit_file_commands"].items()
        }
        validated_options["command_line_args"] = [
            str(argument) for argument in validated_options["command_line_args"]
        ]
        validated_options["job_runner_command"] = str(
            validated_options["job_runner_command"]
        )
        validated_options["submit_filename"] = str(validated_options["submit_filename"])
        validated_options["submit_binary"] = str(validated_options["submit_binary"])
        return validated_options

    if backend == "slurm":
        allowed_top_level_keys = {
            "submit_script_renderer",
            "submit_script_renderer_kwargs",
            "command_line_args",
            "submit_filename",
            "job_folders_filename",
            "submit_binary",
        }
        unknown_keys = set(backend_options.keys()).difference(allowed_top_level_keys)
        if len(unknown_keys) > 0:
            raise GateJobsBackendError(
                f"The slurm backend received unknown option groups: {sorted(unknown_keys)}."
            )

        validated_options = dict(backend_options)
        validated_options.setdefault("submit_script_renderer_kwargs", {})
        validated_options.setdefault("command_line_args", [])
        validated_options.setdefault("submit_filename", SLURM_SUBMIT_FILENAME)
        validated_options.setdefault("job_folders_filename", SLURM_JOB_FOLDERS_FILENAME)
        validated_options.setdefault("submit_binary", "sbatch")

        if "submit_script_renderer" not in validated_options:
            raise GateJobsBackendError(
                "The slurm backend requires a submit_script_renderer callable."
            )
        if not callable(validated_options["submit_script_renderer"]):
            raise GateJobsBackendError(
                "The slurm backend requires submit_script_renderer to be callable."
            )
        if not isinstance(validated_options["submit_script_renderer_kwargs"], dict):
            raise GateJobsBackendError(
                "The slurm backend requires submit_script_renderer_kwargs to be a dictionary."
            )
        if not isinstance(validated_options["command_line_args"], (list, tuple)):
            raise GateJobsBackendError(
                "The slurm backend requires command_line_args to be a list or tuple."
            )

        validated_options["command_line_args"] = [
            str(argument) for argument in validated_options["command_line_args"]
        ]
        validated_options["submit_filename"] = str(validated_options["submit_filename"])
        validated_options["job_folders_filename"] = str(
            validated_options["job_folders_filename"]
        )
        validated_options["submit_binary"] = str(validated_options["submit_binary"])
        return validated_options

    raise GateJobsBackendError(f"Unknown jobs backend '{backend}'.")


def jobs_run(
    split_path,
    backend="local_sequential",
    backend_options=None,
    force=False,
    restart_running_jobs=False,
):
    """Launch a split-jobs campaign from a split root folder or manifest path.

    Local execution backends launch the whole campaign in a separate
    orchestration process so this function can return immediately while the
    selected job folders keep running in the background. External scheduler
    backends submit synchronously instead, so submission errors are reported
    directly to the caller while the actual job execution remains asynchronous.
    """
    manifest_path, manifest = _load_jobs_manifest(split_path)
    split_root_folder = manifest_path.parent
    status_data = get_jobs_status(split_root_folder)

    structurally_not_ready_jobs = [
        job for job in status_data["jobs"] if job.get("status") != "ready"
    ]
    if len(structurally_not_ready_jobs) > 0:
        problematic_jobs = ", ".join(
            job["folder_name"] for job in structurally_not_ready_jobs
        )
        fatal(
            "Cannot run split jobs because some job folders are not structurally ready: "
            f"{problematic_jobs}."
        )

    backend_options = _validate_jobs_backend_options(backend, backend_options)

    running_jobs = []
    selected_job_folders = []
    skipped_completed_jobs = []

    for job_item in manifest.get("jobs", []):
        job_folder = split_root_folder / job_item["folder_name"]
        execution_status = load_job_execution_status(job_folder)
        if execution_status is None:
            selected_job_folders.append(job_folder)
            continue

        if execution_status.get("status") == "completed" and force is False:
            skipped_completed_jobs.append(job_folder)
            continue

        if (
            execution_status.get("status") == "running"
            and restart_running_jobs is False
        ):
            running_jobs.append(job_folder.name)
            continue

        selected_job_folders.append(job_folder)

    if len(running_jobs) > 0:
        fatal(
            "Some jobs are still marked as running: "
            f"{', '.join(running_jobs)}. "
            "Relaunch with restart_running_jobs=True to override them."
        )

    if len(selected_job_folders) == 0:
        return {
            "backend": backend,
            "manifest_path": str(manifest_path),
            "split_root_folder": str(split_root_folder),
            "submitted_jobs": 0,
            "skipped_completed_jobs": len(skipped_completed_jobs),
            "campaign_process_pid": None,
        }

    if backend == "htcondor":
        submission_summary = _submit_job_folders_to_htcondor(
            split_root_folder,
            selected_job_folders,
            backend_options,
            len(skipped_completed_jobs),
        )
        return {
            "backend": backend,
            "manifest_path": str(manifest_path),
            "split_root_folder": str(split_root_folder),
            "submitted_jobs": len(selected_job_folders),
            "skipped_completed_jobs": len(skipped_completed_jobs),
            "campaign_process_pid": None,
            **submission_summary,
        }

    if backend == "slurm":
        submission_summary = _submit_job_folders_to_slurm(
            split_root_folder,
            selected_job_folders,
            backend_options,
            len(skipped_completed_jobs),
        )
        return {
            "backend": backend,
            "manifest_path": str(manifest_path),
            "split_root_folder": str(split_root_folder),
            "submitted_jobs": len(selected_job_folders),
            "skipped_completed_jobs": len(skipped_completed_jobs),
            "campaign_process_pid": None,
            **submission_summary,
        }

    if backend in ("local_sequential", "local_pool"):
        launcher_context = multiprocessing.get_context(
            _get_platform_process_start_method()
        )
        campaign_process = launcher_context.Process(
            # This subprocess is only the campaign orchestrator. Backend-specific
            # job execution happens inside it, potentially with further worker
            # processes or per-job subprocesses depending on the backend.
            target=_run_jobs_campaign,
            args=(
                [str(job_folder) for job_folder in selected_job_folders],
                backend,
                backend_options,
            ),
        )
        campaign_process.start()

        _write_jobs_backend_status(
            split_root_folder,
            backend=backend,
            status="submitted",
            submitted_jobs=len(selected_job_folders),
            skipped_completed_jobs=len(skipped_completed_jobs),
            submitted_at=_now_isoformat(),
            campaign_process_pid=campaign_process.pid,
        )

        return {
            "backend": backend,
            "manifest_path": str(manifest_path),
            "split_root_folder": str(split_root_folder),
            "submitted_jobs": len(selected_job_folders),
            "skipped_completed_jobs": len(skipped_completed_jobs),
            "campaign_process_pid": campaign_process.pid,
            "backend_status_path": str(
                _get_jobs_backend_status_path(split_root_folder)
            ),
        }

    raise GateJobsBackendError(f"Unknown jobs backend '{backend}'.")


def _load_master_simulation_from_manifest(manifest_path, manifest):
    master_simulation_filename = manifest.get(
        "master_simulation_filename", MASTER_SIMULATION_FILENAME
    )
    master_simulation_path = manifest_path.parent / master_simulation_filename
    if not master_simulation_path.exists():
        fatal(
            f"Master simulation file not found at '{master_simulation_path}'. "
            "Cannot initialize jobs merge."
        )
    return create_sim_from_json(master_simulation_path)


def _collect_leaf_merge_sources(manifest_path, manifest):
    split_root_folder = manifest_path.parent
    master_simulation_id = manifest.get("simulation_id")
    original_run_timing_intervals = manifest.get("original_run_timing_intervals", [])
    leaf_sources = []

    for job_item in manifest.get("jobs", []):
        job_folder = split_root_folder / job_item["folder_name"]
        metadata = _load_job_metadata(job_folder)
        parent_simulation_id = metadata.get("parent_simulation_id")
        if parent_simulation_id != master_simulation_id:
            raise GateMergeError(
                f"Job folder '{job_folder}' belongs to parent simulation id "
                f"'{parent_simulation_id}', but the manifest expects "
                f"'{master_simulation_id}'."
            )
        simulation_filename = metadata.get(
            "simulation_filename", JOB_SIMULATION_FILENAME
        )
        simulation_path = job_folder / simulation_filename
        leaf_sources.append(
            {
                "source_kind": "leaf_job",
                "job_id": metadata.get("job_id", job_item.get("job_id")),
                "job_index": metadata.get("job_index", job_item.get("job_index")),
                "folder_name": job_item["folder_name"],
                "folder": job_folder,
                "metadata": metadata,
                "simulation_path": simulation_path,
                "master_simulation_id": parent_simulation_id,
                "original_run_timing_intervals": original_run_timing_intervals,
                "local_run_to_original_run_map": list(
                    metadata.get("original_run_indices", [])
                ),
            }
        )

    return leaf_sources


def _build_original_run_to_sources_map(leaf_sources, original_run_timing_intervals):
    original_run_to_sources_map = {
        original_run_index: []
        for original_run_index in range(len(original_run_timing_intervals))
    }

    for source in leaf_sources:
        local_to_original_run_map = source["local_run_to_original_run_map"]
        local_run_timing_intervals = source["metadata"].get("run_timing_intervals", [])
        if len(local_to_original_run_map) != len(local_run_timing_intervals):
            raise GateMergeError(
                f"Leaf source '{source['folder']}' has inconsistent run metadata: "
                f"{len(local_to_original_run_map)} original run indices for "
                f"{len(local_run_timing_intervals)} local run timing intervals."
            )

        for local_run_index, original_run_index in enumerate(local_to_original_run_map):
            if original_run_index not in original_run_to_sources_map:
                raise GateMergeError(
                    f"Leaf source '{source['folder']}' refers to original run index "
                    f"{original_run_index}, but the master simulation defines only "
                    f"{len(original_run_timing_intervals)} runs."
                )
            original_run_to_sources_map[original_run_index].append(
                {
                    "source_kind": source["source_kind"],
                    "job_id": source["job_id"],
                    "job_index": source["job_index"],
                    "folder": source["folder"],
                    "simulation_path": source["simulation_path"],
                    "local_run_index": local_run_index,
                    "original_run_index": original_run_index,
                    "local_run_timing_interval": local_run_timing_intervals[
                        local_run_index
                    ],
                }
            )

    return original_run_to_sources_map


class RootMergeContextView:
    """Read-only view exposing only ROOT-output merge planning information."""

    def __init__(self, merge_context):
        self._merge_context = merge_context

    def get_source_info(self, job_index):
        return (
            self._merge_context.get_informative().get("sources", {}).get(job_index, {})
        )

    def iter_output_plans(self):
        """Yield one deduplicated ROOT-output plan per target actor/output pair."""
        seen = set()
        for output_plan in self._merge_context.get_output_inventory():
            if output_plan.get("merge_coordinator") != "root":
                continue
            key = (output_plan.get("actor_name"), output_plan.get("output_name"))
            if key in seen:
                continue
            seen.add(key)
            yield output_plan

    def get_contributions_for_output(self, actor_name, output_name):
        contributions = []
        for output_plan in self._merge_context.get_output_inventory():
            if (
                output_plan.get("merge_coordinator") == "root"
                and output_plan.get("actor_name") == actor_name
                and output_plan.get("output_name") == output_name
            ):
                contributions.extend(output_plan.get("contributions", []))
        return contributions


class StandardMergeContextView:
    """Read-only view exposing standard non-ROOT merge planning information."""

    def __init__(self, merge_context):
        self._merge_context = merge_context

    def get_source_info(self, job_index):
        return (
            self._merge_context.get_informative().get("sources", {}).get(job_index, {})
        )

    def iter_output_plans(self):
        seen = set()
        for output_plan in self._merge_context.get_output_inventory():
            if output_plan.get("merge_coordinator") != "standard":
                continue
            key = (output_plan.get("actor_name"), output_plan.get("output_name"))
            if key in seen:
                continue
            seen.add(key)
            yield output_plan

    def get_contributions_for_output(self, actor_name, output_name):
        contributions = []
        for output_plan in self._merge_context.get_output_inventory():
            if (
                output_plan.get("merge_coordinator") == "standard"
                and output_plan.get("actor_name") == actor_name
                and output_plan.get("output_name") == output_name
            ):
                contributions.extend(output_plan.get("contributions", []))
        return contributions


class _CoordinatorOutputMergeContext:
    """Minimal output-scoped execution context consumed by ActorOutput classes."""

    def __init__(self, contributions, load_mode="rehydrated"):
        self._contributions = list(contributions)
        self._load_mode = load_mode

    def get_contributions(self):
        return self._contributions

    def get_load_mode(self, default="rehydrated"):
        return self._load_mode if self._load_mode is not None else default


class StandardMergeCoordinator:
    """Execute and finalize merge for standard non-ROOT actor outputs."""

    def __init__(self):
        self._output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}

    def configure_from_context(self, standard_context, target_simulation):
        self._output_groups = {}
        self._source_infos = {}
        self._source_simulations_by_job_index = {}

        for output_plan in standard_context.iter_output_plans():
            actor_name = output_plan["actor_name"]
            output_name = output_plan["output_name"]
            actor = target_simulation.get_actor(actor_name)
            target_output = actor.user_output.get(output_name)
            if target_output is None:
                raise GateMergeError(
                    f"Cannot configure standard merge for unknown output '{output_name}' "
                    f"on actor '{actor_name}'."
                )
            if target_output.is_container_output() is not True:
                actor.warn_user(
                    f"Skipping unmergeable actor output '{output_name}' "
                    f"from actor '{actor_name}' during merge coordination. "
                    "Only container-based actor outputs are currently handled "
                    "by the jobs-merge framework."
                )
                continue
            contributions = standard_context.get_contributions_for_output(
                actor_name, output_name
            )
            contributions_by_job = {}
            for contribution in contributions:
                if contribution.get("mergeable") is not True:
                    continue
                job_index = contribution["job_index"]
                contributions_by_job.setdefault(job_index, []).append(contribution)
                self._source_infos[job_index] = standard_context.get_source_info(
                    job_index
                )
            self._output_groups[(actor_name, output_name)] = {
                "target_output": target_output,
                "contributions_by_job": contributions_by_job,
            }

    def _get_source_simulation(self, job_index):
        if job_index not in self._source_simulations_by_job_index:
            source_info = self._source_infos[job_index]
            child_simulation = create_sim_from_json(source_info["simulation_path"])
            child_simulation.output_dir = Path(source_info["folder"])
            self._source_simulations_by_job_index[job_index] = child_simulation
        return self._source_simulations_by_job_index[job_index]

    def execute_merge(self):
        for (actor_name, output_name), group in self._output_groups.items():
            target_output = group["target_output"]
            for job_index, contributions in group["contributions_by_job"].items():
                source_simulation = self._get_source_simulation(job_index)
                source_actor = source_simulation.get_actor(actor_name)
                source_output = source_actor.user_output[output_name]
                try:
                    target_output.execute_merge(
                        source_output,
                        context=_CoordinatorOutputMergeContext(contributions),
                    )
                except Exception as error:
                    if isinstance(error, GateMergeError):
                        raise GateMergeError(
                            f"Failed to execute standard merge for actor output "
                            f"'{output_name}' of actor '{actor_name}' from job_index "
                            f"{job_index}."
                        ) from error
                    raise GateMergeError(
                        f"Unexpected failure while executing standard merge for "
                        f"actor output '{output_name}' of actor '{actor_name}' "
                        f"from job_index {job_index}."
                    ) from error

    def finalize_merge(self):
        for (actor_name, output_name), group in self._output_groups.items():
            try:
                group["target_output"].finalize_merge()
            except Exception as error:
                if isinstance(error, GateMergeError):
                    raise GateMergeError(
                        f"Failed to finalize standard merge for actor output "
                        f"'{output_name}' of actor '{actor_name}'."
                    ) from error
                raise GateMergeError(
                    f"Unexpected failure while finalizing standard merge for actor "
                    f"output '{output_name}' of actor '{actor_name}'."
                ) from error


class MergeContext:
    """Campaign-wide merge planning state plus flat output inventory helpers.

    All merge data lives exclusively in the underlying payload. The canonical
    instructive layer is a flat output inventory: one entry per source job and
    actor output, each carrying the contributions planned for that output.
    """

    def __init__(self, payload=None):
        if payload is None:
            payload = {
                "informative": {"sources": {}},
                "instructive": {"output_inventory": []},
            }
        self._payload = payload

    def to_dict(self):
        return self._payload

    def format_pretty(self):
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str)

    def print_pretty(self):
        pretty = self.format_pretty()
        print(pretty)
        return pretty

    def get_informative(self):
        return self._payload.setdefault("informative", {"sources": {}})

    def get_instructive(self):
        return self._payload.setdefault("instructive", {"output_inventory": []})

    def get_output_inventory(self):
        return self.get_instructive().setdefault("output_inventory", [])

    def ensure_source(self, job_index):
        informative_sources = self.get_informative().setdefault("sources", {})
        informative_sources.setdefault(job_index, {})

    def set_source_info(self, job_index, source_info):
        self.ensure_source(job_index)
        self.get_informative()["sources"][job_index] = source_info

    def set_output_plan(self, job_index, actor_name, output_name, output_plan):
        output_plan = dict(output_plan)
        output_plan["job_index"] = job_index
        output_plan["actor_name"] = actor_name
        output_plan["output_name"] = output_name
        inventory = self.get_output_inventory()
        for i, existing_plan in enumerate(inventory):
            if (
                existing_plan.get("job_index") == job_index
                and existing_plan.get("actor_name") == actor_name
                and existing_plan.get("output_name") == output_name
            ):
                inventory[i] = output_plan
                return
        inventory.append(output_plan)

    def append_contribution(self, job_index, actor_name, output_name, contribution):
        for output_plan in self.get_output_inventory():
            if (
                output_plan.get("job_index") == job_index
                and output_plan.get("actor_name") == actor_name
                and output_plan.get("output_name") == output_name
            ):
                output_plan.setdefault("contributions", []).append(contribution)
                return
        fatal(
            f"Cannot append merge contribution because no output plan exists for "
            f"job_index={job_index}, actor_name='{actor_name}', output_name='{output_name}'."
        )

    def enrich_source_contributions_with_campaign_mapping(
        self,
        job_index,
        local_to_original_run_map,
        job_id,
        source_simulation_id,
    ):
        for output_plan in self.get_output_inventory():
            if output_plan.get("job_index") != job_index:
                continue
            for contribution in output_plan.get("contributions", []):
                source_scope = contribution.get("source_scope")
                if source_scope == "merged":
                    contribution["target_scope"] = "merged"
                else:
                    try:
                        contribution["target_scope"] = local_to_original_run_map[
                            int(source_scope)
                        ]
                    except (IndexError, TypeError, ValueError) as error:
                        raise GateMergeError(
                            f"Cannot map local source scope {source_scope!r} for "
                            f"job_index={job_index}, job_id={job_id}. "
                            f"Available local_to_original_run_map is "
                            f"{local_to_original_run_map}."
                        ) from error
                contribution["job_index"] = job_index
                contribution["job_id"] = job_id
                contribution["source_simulation_id"] = source_simulation_id

    def get_root_view(self):
        return RootMergeContextView(self)

    def get_standard_view(self):
        return StandardMergeContextView(self)


class JobsMergeManager:
    """Campaign-level orchestrator for merging split simulation results.

    Phase 1 supports sequential orchestration over leaf job folders only. The
    manager rehydrates the persisted master simulation as the merge target and
    uses per-job metadata to align each child-local run index with the original
    run index of the master simulation.
    """

    def __init__(self, split_path, output_dir=None, **options):
        self.manifest_path, self.manifest = _load_jobs_manifest(split_path)
        self.split_root_folder = self.manifest_path.parent
        self.output_dir = None if output_dir is None else Path(output_dir).resolve()
        self.options = dict(options)
        self.master_simulation = None
        self.leaf_sources = []
        self.original_run_to_sources_map = {}
        self.child_simulations_by_job_id = {}
        self.remaining_local_runs_by_job_id = {}
        self._merge_result = None
        self._total_merge_duration = None
        self._merge_start_time = None
        self._planning_start_time = None
        self._planning_duration = None
        self._execution_start_time = None
        self._execution_duration = None
        self._merge_planned = False
        self._merge_executed = False
        self._merge_finalized = False
        self.merge_context = None
        self.standard_merge_coordinator = None
        self.root_merge_coordinator = None

    @property
    def merge_result(self):
        if self._merge_result is None:
            return None
        return {
            **self._merge_result,
            "total_merge_duration": self.total_merge_duration,
        }

    @property
    def total_merge_duration(self):
        return self._total_merge_duration

    @property
    def planning_duration(self):
        return self._planning_duration

    @property
    def execution_duration(self):
        return self._execution_duration

    @property
    def merge_planned(self):
        return self._merge_planned

    @property
    def merge_executed(self):
        return self._merge_executed

    @property
    def merge_finalized(self):
        return self._merge_finalized

    def load_campaign_metadata(self):
        self.leaf_sources = _collect_leaf_merge_sources(
            self.manifest_path, self.manifest
        )
        self.original_run_to_sources_map = _build_original_run_to_sources_map(
            self.leaf_sources, self.manifest.get("original_run_timing_intervals", [])
        )
        self.remaining_local_runs_by_job_id = {
            source["job_id"]: set(range(len(source["local_run_to_original_run_map"])))
            for source in self.leaf_sources
        }

    def rehydrate_master_simulation(self):
        self.master_simulation = _load_master_simulation_from_manifest(
            self.manifest_path, self.manifest
        )
        if self.output_dir is not None:
            self.master_simulation.output_dir = self.output_dir
        return self.master_simulation

    def create_merge_context(self):
        self.merge_context = MergeContext()
        return self.merge_context

    def iter_original_run_contributions(self):
        for (
            original_run_index,
            contributions,
        ) in self.original_run_to_sources_map.items():
            yield original_run_index, contributions

    def _get_leaf_source(self, job_id):
        for source in self.leaf_sources:
            if source["job_id"] == job_id:
                return source
        fatal(f"Cannot find leaf merge source for job_id '{job_id}'.")

    def _get_child_simulation(self, contribution):
        job_id = contribution["job_id"]
        if job_id not in self.child_simulations_by_job_id:
            source = self._get_leaf_source(job_id)
            child_simulation = create_sim_from_json(source["simulation_path"])
            child_simulation.output_dir = source["folder"]
            self.child_simulations_by_job_id[job_id] = child_simulation
        return self.child_simulations_by_job_id[job_id]

    def _release_child_simulation_if_done(self, contribution):
        job_id = contribution["job_id"]
        remaining_local_runs = self.remaining_local_runs_by_job_id[job_id]
        remaining_local_runs.discard(contribution["local_run_index"])
        if len(remaining_local_runs) == 0:
            self.child_simulations_by_job_id.pop(job_id, None)

    def build_merge_plan(self):
        return self.plan_merge().to_dict()

    def plan_merge(self, mode="as_configured"):
        from .rootio import RootMergeCoordinator

        if self.master_simulation is None:
            self.rehydrate_master_simulation()
        if len(self.leaf_sources) == 0 and len(self.original_run_to_sources_map) == 0:
            self.load_campaign_metadata()
        self._planning_start_time = time.perf_counter()
        merge_context = self.create_merge_context()

        informative = merge_context.get_informative()
        informative.update(
            {
                "target_simulation_id": self.manifest.get("simulation_id"),
                "split_root_folder": str(self.split_root_folder),
                "manifest_path": str(self.manifest_path),
                "original_run_timing_intervals": _copy_run_timing_intervals(
                    self.manifest.get("original_run_timing_intervals", [])
                ),
                "number_of_children_per_original_run": {
                    original_run_index: len(contributions)
                    for original_run_index, contributions in self.iter_original_run_contributions()
                },
            }
        )

        for source in self.leaf_sources:
            job_index = source["job_index"]
            merge_context.set_source_info(
                job_index,
                {
                    "job_id": source["job_id"],
                    "source_simulation_id": source["metadata"].get("simulation_id"),
                    "folder_name": source["folder_name"],
                    "folder": str(source["folder"]),
                    "simulation_path": str(source["simulation_path"]),
                    "local_to_original_run_map": list(
                        source.get("local_run_to_original_run_map", [])
                    ),
                },
            )
            child_simulation = create_sim_from_json(source["simulation_path"])
            child_simulation.output_dir = source["folder"]
            output_plans = child_simulation.plan_merge(mode=mode)
            for output_plan in output_plans:
                merge_context.set_output_plan(
                    job_index,
                    output_plan["actor_name"],
                    output_plan["output_name"],
                    output_plan,
                )
            merge_context.enrich_source_contributions_with_campaign_mapping(
                job_index=job_index,
                local_to_original_run_map=list(
                    source.get("local_run_to_original_run_map", [])
                ),
                job_id=source["job_id"],
                source_simulation_id=source["metadata"].get("simulation_id"),
            )

        self.standard_merge_coordinator = StandardMergeCoordinator()
        self.standard_merge_coordinator.configure_from_context(
            merge_context.get_standard_view(),
            self.master_simulation,
        )
        self.root_merge_coordinator = RootMergeCoordinator()
        self.root_merge_coordinator.configure_from_context(
            merge_context.get_root_view(),
            self.master_simulation,
        )
        self.master_simulation.set_merge_coordinators(
            [
                self.standard_merge_coordinator,
                self.root_merge_coordinator,
            ]
        )
        if self._planning_start_time is not None:
            self._planning_duration = time.perf_counter() - self._planning_start_time
        self._merge_planned = True
        self._merge_executed = False
        self._merge_finalized = False
        return merge_context

    def build_summary_dict(self):
        if self.master_simulation is None:
            self.rehydrate_master_simulation()
        if len(self.leaf_sources) == 0 and len(self.original_run_to_sources_map) == 0:
            self.load_campaign_metadata()

        merged_output_dir = (
            self.output_dir
            if self.output_dir is not None
            else self.master_simulation.output_dir
        )
        return {
            "manifest_path": str(self.manifest_path),
            "split_root_folder": str(self.split_root_folder),
            "master_simulation_id": self.manifest.get("simulation_id"),
            "merged_output_dir": str(merged_output_dir),
            "number_of_leaf_sources": len(self.leaf_sources),
            "number_of_original_runs": len(
                self.manifest.get("original_run_timing_intervals", [])
            ),
            "original_run_timing_intervals": _copy_run_timing_intervals(
                self.manifest.get("original_run_timing_intervals", [])
            ),
            "source_jobs": [
                {
                    "folder_name": source["folder_name"],
                    "folder": str(source["folder"]),
                    "job_id": source["job_id"],
                    "job_index": source["job_index"],
                    "original_runs": list(
                        source.get("local_run_to_original_run_map", [])
                    ),
                    "local_run_timing_intervals": _copy_run_timing_intervals(
                        source["metadata"].get("run_timing_intervals", [])
                    ),
                }
                for source in self.leaf_sources
            ],
            "merge_plan_by_original_run": {
                str(original_run_index): [
                    {
                        "folder_name": Path(contribution["folder"]).name,
                        "folder": str(contribution["folder"]),
                        "job_id": contribution["job_id"],
                        "job_index": contribution["job_index"],
                        "local_run_index": contribution["local_run_index"],
                    }
                    for contribution in contributions
                ]
                for original_run_index, contributions in self.iter_original_run_contributions()
            },
            "total_merge_duration": self.total_merge_duration,
            "planning_duration": self.planning_duration,
            "execution_duration": self.execution_duration,
            "merge_planned": self.merge_planned,
            "merge_executed": self.merge_executed,
            "merge_finalized": self.merge_finalized,
            "merge_completed": self.merge_result is not None,
        }

    def format_merge_summary(self):
        if self.master_simulation is None:
            self.rehydrate_master_simulation()
        if len(self.leaf_sources) == 0 and len(self.original_run_to_sources_map) == 0:
            self.load_campaign_metadata()

        merged_output_dir = (
            self.output_dir
            if self.output_dir is not None
            else self.master_simulation.output_dir
        )
        lines = [
            "Jobs merge summary:",
            f"- source master folder: {self.split_root_folder}",
            f"| target merged folder: {merged_output_dir}",
            f"| master simulation id: {self.manifest.get('simulation_id', 'Unknown')}",
            f"| original run timing intervals: {_format_timing_intervals(self.manifest.get('original_run_timing_intervals', []))}",
        ]
        if self.total_merge_duration is not None:
            lines.append(f"| total merge duration: {self.total_merge_duration:.3f} s")
        if self.planning_duration is not None:
            lines.append(f"| planning duration: {self.planning_duration:.3f} s")
        if self.execution_duration is not None:
            lines.append(f"| execution duration: {self.execution_duration:.3f} s")
        lines.append(f"| merge planned: {self.merge_planned}")
        lines.append(f"| merge executed: {self.merge_executed}")
        lines.append(f"| merge finalized: {self.merge_finalized}")
        lines.append("| source job folders:")
        for source in self.leaf_sources:
            lines.extend(
                [
                    f"| - {source['folder_name']}",
                    f"|   | folder: {source['folder']}",
                    f"|   | original runs: {_format_original_run_indices(source.get('local_run_to_original_run_map', []))}",
                    f"|   | local timing intervals: {_format_timing_intervals(source['metadata'].get('run_timing_intervals', []))}",
                ]
            )
        lines.append("| merge plan by original run:")
        for original_run_index, contributions in self.iter_original_run_contributions():
            contribution_str = ", ".join(
                f"{Path(contribution['folder']).name}(local {contribution['local_run_index']})"
                for contribution in contributions
            )
            lines.extend(
                [
                    f"| - run {original_run_index}",
                    f"|   | contributors: {contribution_str}",
                ]
            )
        return "\n".join(lines)

    def print_merge_summary(self):
        summary = self.format_merge_summary()
        print(summary)
        return summary

    def save_summary_json(self, path):
        summary_path = Path(path)
        with open(summary_path, "w") as output_file:
            dump_json(self.build_summary_dict(), output_file)
        return summary_path

    def save_summary_text(self, path):
        summary_path = Path(path)
        with open(summary_path, "w") as output_file:
            output_file.write(self.format_merge_summary())
            output_file.write("\n")
        return summary_path

    def execute_merge(self):
        if self._merge_planned is not True:
            raise GateMergeError(
                "JobsMergeManager.execute_merge() requires planning to be completed first. "
                "Call plan_merge() before execute_merge(), or use merge()."
            )
        if self.master_simulation is None or self.merge_context is None:
            raise GateMergeError(
                "JobsMergeManager.execute_merge() is in an inconsistent state: "
                "merge_planned is True but the prepared simulation or merge context is missing."
            )
        if len(self.master_simulation._merge_coordinators) == 0:
            raise GateMergeError(
                "JobsMergeManager.execute_merge() found no prepared merge coordinators. "
                "Call plan_merge() before execute_merge(), or use merge()."
            )
        self._execution_start_time = time.perf_counter()
        self.master_simulation.execute_merge()
        self._merge_executed = True

    def finalize_merge(self):
        if self._merge_planned is not True:
            raise GateMergeError(
                "JobsMergeManager.finalize_merge() requires planning to be completed first. "
                "Call plan_merge() before finalize_merge(), or use merge()."
            )
        if self.master_simulation is None or self.merge_context is None:
            raise GateMergeError(
                "JobsMergeManager.finalize_merge() is in an inconsistent state: "
                "merge_planned is True but the prepared simulation or merge context is missing."
            )
        if len(self.master_simulation._merge_coordinators) == 0:
            raise GateMergeError(
                "JobsMergeManager.finalize_merge() found no prepared merge coordinators. "
                "Call plan_merge() before finalize_merge(), or use merge()."
            )
        if self._merge_executed is not True:
            raise GateMergeError(
                "JobsMergeManager.finalize_merge() requires execute_merge() to have run first. "
                "Call execute_merge() before finalize_merge(), or use merge()."
            )
        self.master_simulation.finalize_merge()
        if self._execution_start_time is not None:
            self._execution_duration = time.perf_counter() - self._execution_start_time
        if self._merge_start_time is not None:
            self._total_merge_duration = time.perf_counter() - self._merge_start_time
        self._merge_finalized = True
        self._merge_result = {
            "manifest_path": str(self.manifest_path),
            "split_root_folder": str(self.split_root_folder),
            "master_simulation_id": self.manifest.get("simulation_id"),
            "merged_output_dir": str(self.master_simulation.output_dir),
            "number_of_leaf_sources": len(self.leaf_sources),
            "number_of_original_runs": len(
                self.manifest.get("original_run_timing_intervals", [])
            ),
            "planning_duration": self.planning_duration,
            "execution_duration": self.execution_duration,
            "total_merge_duration": self.total_merge_duration,
            "merge_planned": self.merge_planned,
            "merge_executed": self.merge_executed,
            "merge_finalized": self.merge_finalized,
        }

    def merge(self):
        if self.master_simulation is None:
            self.rehydrate_master_simulation()
        if len(self.leaf_sources) == 0 and len(self.original_run_to_sources_map) == 0:
            self.load_campaign_metadata()

        self._merge_start_time = time.perf_counter()
        if self._merge_planned is not True:
            self.plan_merge()
        if self._merge_executed is not True:
            self.execute_merge()
        if self._merge_finalized is not True:
            self.finalize_merge()
        return self._merge_result


def jobs_merge(from_path, to_path=None, execute=True, **options):
    merge_manager = JobsMergeManager(from_path, output_dir=to_path, **options)
    merge_manager.rehydrate_master_simulation()
    merge_manager.load_campaign_metadata()
    if execute:
        merge_manager.merge()
    return merge_manager


def format_jobs_merge_summary(from_path, to_path=None, **options):
    merge_manager = JobsMergeManager(from_path, output_dir=to_path, **options)
    merge_manager.rehydrate_master_simulation()
    merge_manager.load_campaign_metadata()
    return merge_manager.format_merge_summary()


def print_jobs_merge_summary(from_path, to_path=None, **options):
    merge_manager = JobsMergeManager(from_path, output_dir=to_path, **options)
    merge_manager.rehydrate_master_simulation()
    merge_manager.load_campaign_metadata()
    return merge_manager.print_merge_summary()


from .base import (
    _get_user_info_options,
    find_all_gate_objects,
    find_all_paths,
)
from .managers import create_sim_from_json


def _find_metaimage_payload_paths(header_path):
    payload_paths = []
    if not header_path.exists():
        return payload_paths
    try:
        with open(header_path, "r") as header_file:
            for line in header_file:
                if "=" not in line:
                    continue
                key, value = [part.strip() for part in line.split("=", 1)]
                if key != "ElementDataFile":
                    continue
                if value.upper() == "LOCAL":
                    return []
                payload_path = Path(value)
                if not payload_path.is_absolute():
                    payload_path = header_path.parent / payload_path
                payload_paths.append(payload_path)
                break
    except OSError:
        pass
    return payload_paths


def _get_simulation_input_files_info(simulation):
    input_files_info = []
    dct = simulation.to_dictionary()
    for go_dict in find_all_gate_objects(dct):
        obj_name = go_dict["user_info"].get("name", go_dict.get("name", "Unknown"))
        class_name = go_dict.get("object_type", "Unknown")
        class_module = go_dict.get("class_module", "")

        for ui_name, ui_value in go_dict["user_info"].items():
            if ui_value is None:
                continue
            options = _get_user_info_options(ui_name, class_name, class_module)
            if options.get("is_input_file") is True:
                paths = find_all_paths(ui_value)
                for p in paths:
                    input_files_info.append(
                        {
                            "object_name": obj_name,
                            "class_name": class_name,
                            "attribute": ui_name,
                            "value": str(p),
                        }
                    )
                    path_obj = Path(p)
                    if path_obj.suffix.lower() == ".mhd":
                        for payload in _find_metaimage_payload_paths(path_obj):
                            input_files_info.append(
                                {
                                    "object_name": obj_name,
                                    "class_name": class_name,
                                    "attribute": f"{ui_name} payload",
                                    "value": str(payload),
                                }
                            )

    if (
        hasattr(simulation, "volume_manager")
        and simulation.volume_manager.material_database is not None
    ):
        for fn in simulation.volume_manager.material_database.filenames:
            input_files_info.append(
                {
                    "object_name": "MaterialDatabase",
                    "class_name": "MaterialDatabase",
                    "attribute": "filenames",
                    "value": str(fn),
                }
            )

    return input_files_info


def _format_bytes(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        val = size_bytes / (1024 * 1024)
        if val == int(val):
            return f"{int(val)} MB"
        return f"{val:.1f} MB"
    else:
        val = size_bytes / (1024 * 1024 * 1024)
        return f"{val:.1f} GB"


def get_jobs_status(manifest_or_dir_path):
    path = Path(manifest_or_dir_path).resolve()
    if path.is_dir():
        manifest_path = path / JOBS_MANIFEST_FILENAME
    else:
        manifest_path = path

    if not manifest_path.exists():
        fatal(f"Jobs manifest file not found at '{manifest_path}'.")

    with open(manifest_path, "r") as f:
        manifest = load_json(f)

    split_root_folder = manifest_path.parent

    master_sim_filename = manifest.get(
        "master_simulation_filename", MASTER_SIMULATION_FILENAME
    )
    master_sim_file = split_root_folder / master_sim_filename

    master_input_files = []
    if master_sim_file.exists():
        try:
            master_sim = create_sim_from_json(master_sim_file)
            master_input_files = _get_simulation_input_files_info(master_sim)
        except Exception:
            pass

    status_data = {
        "manifest_path": str(manifest_path),
        "split_root_folder": str(split_root_folder),
        "simulation_id": manifest.get("simulation_id", "Unknown"),
        "created_at": manifest.get("created_at", "Unknown"),
        "policy": manifest.get("policy", "Unknown"),
        "number_of_jobs": manifest.get("number_of_jobs", len(manifest.get("jobs", []))),
        "original_run_timing_intervals": manifest.get(
            "original_run_timing_intervals", []
        ),
        "master_simulation_exists": master_sim_file.exists(),
        "master_input_files": master_input_files,
        "backend_status_filename": JOBS_BACKEND_STATUS_FILENAME,
        "backend_status_exists": False,
        "backend_status_data": None,
        "jobs": [],
        "summary_counts": {
            "total": 0,
            "ready": 0,
            "missing_folder": 0,
            "missing_metadata": 0,
            "missing_input_file": 0,
        },
        "execution_counts": {
            "running": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
        },
    }

    backend_status_data = load_jobs_backend_status(split_root_folder)
    if backend_status_data is not None:
        status_data["backend_status_exists"] = True
        status_data["backend_status_data"] = backend_status_data

    for job_item in manifest.get("jobs", []):
        folder_name = job_item.get("folder_name", "")
        job_folder = split_root_folder / folder_name
        metadata_filename = job_item.get("metadata_filename", JOB_METADATA_FILENAME)
        metadata_file = job_folder / metadata_filename

        folder_exists = job_folder.exists()
        metadata_exists = metadata_file.exists()
        metadata = {}
        if metadata_exists:
            with open(metadata_file, "r") as input_file:
                metadata = load_json(input_file)

        execution_status_data = load_job_execution_status(job_folder)
        execution_status = None
        if execution_status_data is not None:
            execution_status = execution_status_data.get("status")
            if execution_status in status_data["execution_counts"]:
                status_data["execution_counts"][execution_status] += 1

        simulation_filename = metadata.get(
            "simulation_filename", JOB_SIMULATION_FILENAME
        )
        simulation_file = job_folder / simulation_filename
        sim_exists = simulation_file.exists()

        folder_size = 0
        has_symlink = False
        if folder_exists:
            for item in job_folder.rglob("*"):
                if item.is_symlink():
                    has_symlink = True
                if item.is_file() or item.is_symlink():
                    try:
                        folder_size += item.stat().st_size
                    except OSError:
                        pass

        missing_input_files = []
        if folder_exists and metadata_exists and sim_exists:
            try:
                child_sim = create_sim_from_json(simulation_file)
                job_input_files = _get_simulation_input_files_info(child_sim)
                for info in job_input_files:
                    val_str = info["value"]
                    val_path = Path(val_str)
                    file_found = (
                        (job_folder / val_path.name).exists()
                        or (
                            not val_path.is_absolute()
                            and (job_folder / val_path).exists()
                        )
                        or (
                            val_path.is_absolute()
                            and val_path.exists()
                            and not metadata_exists
                        )
                    )

                    if not file_found:
                        missing_input_files.append(
                            f"[{info['class_name']}] {info['object_name']} -> {info['attribute']}: {val_str}"
                        )
            except Exception:
                pass

        if not folder_exists:
            job_status = "missing_folder"
        elif not metadata_exists:
            job_status = "missing_metadata"
        elif missing_input_files:
            job_status = "missing_input_file"
        elif sim_exists:
            job_status = "ready"
        else:
            job_status = "unknown"

        status_data["summary_counts"]["total"] += 1
        if job_status in status_data["summary_counts"]:
            status_data["summary_counts"][job_status] += 1

        status_data["jobs"].append(
            {
                # job_index is structural manifest data. Keep it available even
                # when the child metadata file is missing so status reporting can
                # still identify the job robustly.
                "job_index": (
                    metadata.get("job_index")
                    if metadata.get("job_index") is not None
                    else job_item.get("job_index")
                ),
                "job_id": job_item.get("job_id"),
                "folder_name": folder_name,
                "folder_exists": folder_exists,
                "metadata_exists": metadata_exists,
                "simulation_exists": sim_exists,
                "missing_input_files": missing_input_files,
                "status": job_status,
                "run_timing_intervals": metadata.get("run_timing_intervals", []),
                "original_run_indices": metadata.get("original_run_indices", []),
                "folder_size_bytes": folder_size,
                "folder_size_str": _format_bytes(folder_size),
                "input_mode": "linked" if has_symlink else "copied",
                "execution_status_filename": JOB_EXECUTION_STATUS_FILENAME,
                "execution_status_exists": execution_status_data is not None,
                "execution_status": execution_status,
                "execution_status_data": execution_status_data,
            }
        )

    return status_data

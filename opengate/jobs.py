import math
import multiprocessing
import os
import re
import subprocess
import sys
import traceback
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np

from .exception import GateJobsBackendError, fatal
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


def _create_split_root_folder(split_path):
    parent = Path(split_path)
    timestamp = datetime.now().strftime("jobs_%Y%m%d_%H%M%S")
    split_root = parent / timestamp
    suffix = 1
    while split_root.exists():
        split_root = parent / f"{timestamp}_{suffix:02d}"
        suffix += 1
    split_root.mkdir(parents=True, exist_ok=False)
    return split_root.resolve()


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


def _split_time_per_interval(run_timing_intervals, number_of_jobs):
    if number_of_jobs % len(run_timing_intervals) != 0:
        fatal(
            "The split_time policy requires the number of jobs to be a multiple "
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


def _split_time_total(run_timing_intervals, number_of_jobs):
    # Split the total active simulation time into consecutive jobs. Unlike
    # _split_time_per_interval(), a single job may span several original runs.
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
                f"Unable to build split_time_total job {job_index}. "
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
    if policy == "split_time":
        return _split_time_per_interval(run_timing_intervals, number_of_jobs)
    if policy == "split_time_total":
        return _split_time_total(run_timing_intervals, number_of_jobs)
    fatal(
        f"Unknown split policy '{policy}'. "
        "Known policies are: 'split_time', 'split_time_total'."
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
    policy="split_time",
    link_files=False,
    **options,
):
    # Split authoritative, resolved configuration rather than the raw user
    # inputs so child jobs inherit explicit timing anchors and helper actors.
    simulation.resolve_and_validate_config()

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
    split_root_folder = _create_split_root_folder(split_path)
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
        child_simulation.to_json_file(
            directory=job_folder,
            filename=Path(JOB_SIMULATION_FILENAME),
        )
        child_simulation.archive_input_files(
            directory=job_folder, link_files=link_files
        )
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
    with open(_get_jobs_backend_status_path(split_root_folder), "w") as output_file:
        dump_json(status_data, output_file)
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
    with open(_get_job_execution_status_path(job_folder), "w") as output_file:
        dump_json(status_data, output_file)
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
    if int(n_workers) < 1:
        raise GateJobsBackendError("The local_pool backend requires n_workers >= 1.")
    if int(maxtasksperchild) != 1:
        raise GateJobsBackendError(
            "The local_pool backend currently requires maxtasksperchild=1 so each "
            "worker process executes at most one job."
        )
    ctx = multiprocessing.get_context(start_method)
    with ctx.Pool(
        processes=int(n_workers),
        maxtasksperchild=maxtasksperchild,
    ) as pool:
        return pool.map(_run_job_folder_local_pool, [str(p) for p in job_folders])


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
        pooling_options = backend_options.get("pooling_options", {})
        return _run_job_folders_in_local_pool(job_folders, **pooling_options)

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
        allowed_top_level_keys = {"pooling_options"}
        unknown_keys = set(backend_options.keys()).difference(allowed_top_level_keys)
        if len(unknown_keys) > 0:
            raise GateJobsBackendError(
                f"The local_pool backend received unknown option groups: {sorted(unknown_keys)}."
            )
        pooling_options = dict(backend_options.get("pooling_options", {}))
        allowed_pooling_keys = {"n_workers", "start_method", "maxtasksperchild"}
        unknown_pooling_keys = set(pooling_options.keys()).difference(
            allowed_pooling_keys
        )
        if len(unknown_pooling_keys) > 0:
            raise GateJobsBackendError(
                f"The local_pool backend received unknown pooling_options: {sorted(unknown_pooling_keys)}."
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
        return {"pooling_options": pooling_options}

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

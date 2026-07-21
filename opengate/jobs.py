import math
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np

from .exception import fatal
from .runtiming import assert_run_timing
from .serialization import dump_json, load_json

JOBS_MANIFEST_FILENAME = "jobs_manifest.json"
JOB_METADATA_FILENAME = "job_metadata.json"
JOB_SIMULATION_FILENAME = "simulation.json"
MASTER_SIMULATION_FILENAME = "simulation.json"


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
        "folder_name": job_definition["folder_name"],
        "parent_simulation_id": parent_simulation_id,
        "run_timing_intervals": _copy_run_timing_intervals(
            job_definition["run_timing_intervals"]
        ),
        "original_run_indices": list(job_definition["original_run_indices"]),
        "simulation_filename": JOB_SIMULATION_FILENAME,
        "metadata_filename": JOB_METADATA_FILENAME,
    }
    return job_folder, child_metadata


def create_split_jobs(
    simulation, number_of_jobs, split_path, policy="split_time", **options
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
    simulation.archive_input_files(directory=split_root_folder)

    jobs_manifest = {
        "simulation_id": simulation_id,
        "created_at": created_at,
        "policy": policy,
        "options": options,
        "number_of_jobs": number_of_jobs,
        "split_root_folder": str(split_root_folder),
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
        child_simulation.archive_input_files(directory=job_folder)
        with open(job_folder / JOB_METADATA_FILENAME, "w") as output_file:
            dump_json(child_metadata, output_file)
        jobs_manifest["jobs"].append(child_metadata)

    with open(split_root_folder / JOBS_MANIFEST_FILENAME, "w") as output_file:
        dump_json(jobs_manifest, output_file)

    return split_root_folder


from .base import (
    _get_user_info_options,
    find_all_gate_objects,
    find_all_paths,
)
from .managers import create_sim_from_json


def get_simulation_input_files_info(simulation):
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

    split_root_folder = Path(manifest.get("split_root_folder", manifest_path.parent))
    if not split_root_folder.exists():
        split_root_folder = manifest_path.parent

    master_sim_filename = manifest.get(
        "master_simulation_filename", MASTER_SIMULATION_FILENAME
    )
    master_sim_file = split_root_folder / master_sim_filename

    master_input_files = []
    if master_sim_file.exists():
        try:
            master_sim = create_sim_from_json(master_sim_file)
            master_input_files = get_simulation_input_files_info(master_sim)
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
        "jobs": [],
        "summary_counts": {
            "total": 0,
            "ready": 0,
            "missing_folder": 0,
            "missing_metadata": 0,
        },
    }

    for job_item in manifest.get("jobs", []):
        folder_name = job_item.get("folder_name", "")
        job_folder = split_root_folder / folder_name
        metadata_filename = job_item.get("metadata_filename", JOB_METADATA_FILENAME)
        simulation_filename = job_item.get(
            "simulation_filename", JOB_SIMULATION_FILENAME
        )

        metadata_file = job_folder / metadata_filename
        simulation_file = job_folder / simulation_filename

        folder_exists = job_folder.exists()
        metadata_exists = metadata_file.exists()
        sim_exists = simulation_file.exists()

        if not folder_exists:
            job_status = "missing_folder"
        elif not metadata_exists:
            job_status = "missing_metadata"
        elif sim_exists:
            job_status = "ready"
        else:
            job_status = "unknown"

        status_data["summary_counts"]["total"] += 1
        if job_status in status_data["summary_counts"]:
            status_data["summary_counts"][job_status] += 1

        status_data["jobs"].append(
            {
                "job_index": job_item.get("job_index"),
                "job_id": job_item.get("job_id"),
                "folder_name": folder_name,
                "folder_exists": folder_exists,
                "metadata_exists": metadata_exists,
                "simulation_exists": sim_exists,
                "status": job_status,
                "run_timing_intervals": job_item.get("run_timing_intervals", []),
                "original_run_indices": job_item.get("original_run_indices", []),
            }
        )

    return status_data

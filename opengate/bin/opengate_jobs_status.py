#!/usr/bin/env python3

import click
import colored
import opengate_core as g4
from opengate.exception import color_error
from opengate.jobs import get_jobs_status

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def format_timing_intervals(intervals):
    if not intervals:
        return "[]"
    formatted = []
    for interval in intervals:
        start_str = str(g4.G4BestUnit(interval[0], "Time")).strip()
        end_str = str(g4.G4BestUnit(interval[1], "Time")).strip()
        formatted.append(f"[{start_str}, {end_str}]")
    intervals_str = ", ".join(formatted)
    nb_runs = len(intervals)
    return f"{intervals_str}  {nb_runs} run(s)"


def print_jobs_status_summary(status_data, verbose=False):
    intervals = status_data.get("original_run_timing_intervals", [])
    print(f" Manifest file:      {status_data['manifest_path']}")
    print(f" Root directory:     {status_data['split_root_folder']}")
    print(f" Simulation ID:      {status_data['simulation_id']}")
    print(f" Created at:         {status_data['created_at']}")
    print(f" Split policy:       {status_data['policy']}")
    print(f" Number of jobs:     {status_data['number_of_jobs']}")
    print(f" Time intervals:     {format_timing_intervals(intervals)}")
    master_str = (
        "Found"
        if status_data["master_simulation_exists"]
        else colored.stylize("Missing", color_error)
    )
    print(f" Master simulation:  {master_str}")
    master_inputs = status_data.get("master_input_files", [])
    if master_inputs:
        print(" Master input files:")
        for item in master_inputs:
            print(
                f"   - [{item['class_name']}] {item['object_name']} -> {item['attribute']}: {item['value']}"
            )
    else:
        print(" Master input files: None")
    print(" Job Status Summary:")
    counts = status_data["summary_counts"]
    missing_total = (
        counts["missing_folder"]
        + counts["missing_metadata"]
        + counts.get("missing_input_file", 0)
    )
    missing_str = (
        colored.stylize(str(missing_total), color_error)
        if missing_total > 0
        else str(missing_total)
    )
    print(
        f"  Total: {counts['total']}  |  Ready: {counts['ready']}  |  Missing: {missing_str}"
    )
    execution_counts = status_data.get("execution_counts", {})
    if len(execution_counts) > 0:
        print(
            "  Execution: "
            f"running={execution_counts.get('running', 0)}  "
            f"completed={execution_counts.get('completed', 0)}  "
            f"failed={execution_counts.get('failed', 0)}  "
            f"skipped={execution_counts.get('skipped', 0)}"
        )

    for job in status_data["jobs"]:
        job_idx = job["job_index"]
        folder = job["folder_name"]
        st = job["status"].upper()
        st_str = colored.stylize(st, color_error) if st != "READY" else st
        exec_status = job.get("execution_status")
        exec_str = exec_status.upper() if exec_status is not None else "NONE"
        job_intervals = job.get("run_timing_intervals", [])
        timing_str = format_timing_intervals(job_intervals)
        input_mode = job.get("input_mode", "copied")
        size_str = job.get("folder_size_str", "0 B")
        print(
            f"  [Job {job_idx:04d}] {folder}: status = {st_str}, execution = {exec_str}, timing = {timing_str}, inputs = {input_mode} ({size_str})"
        )
        missing_files = job.get("missing_input_files", [])
        if missing_files:
            for missing in missing_files:
                err_msg = f"     Missing input file: {missing}"
                print(colored.stylize(err_msg, color_error))


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("manifest_or_dir", type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Print verbose job metadata")
def go(manifest_or_dir, verbose):
    """
    Print a status summary for an OpenGATE job split campaign given a manifest file or directory.
    """
    status_data = get_jobs_status(manifest_or_dir)
    print_jobs_status_summary(status_data, verbose=verbose)


if __name__ == "__main__":
    go()

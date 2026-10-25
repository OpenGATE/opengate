#!/usr/bin/env python3

import click
import colored
import opengate_core as g4
from opengate.exception import color_error
from opengate.jobs import _format_bytes as format_bytes, jobs_status

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def seconds(t):
    """Time in seconds, 4 significant digits (e.g. 54.85, 115.1, 0.001)"""
    return f"{t / g4.G4UnitDefinition.GetValueOf('s'):.4g}"


def best_unit_time(t):
    return str(g4.G4BestUnit(t, "Time")).strip()


def format_campaign_timing(intervals, verbose=False):
    """
    Runs of the whole campaign: the timeline (start of the first run to the end
    of the last one), the total acquisition time (sum of the run durations) and
    the gaps between the runs (nothing is simulated during the gaps).
    With verbose, the list of all the intervals.
    """
    if not intervals:
        return "no runs"
    if verbose:
        return format_all_intervals(intervals)
    start, end = intervals[0][0], intervals[-1][1]
    acquisition = sum(i[1] - i[0] for i in intervals)
    return (
        f"{len(intervals)} runs, timeline {seconds(start)} to {seconds(end)} s, "
        f"total acquisition time {seconds(acquisition)} s "
        f"(+ {seconds(end - start - acquisition)} s of gaps between runs)"
    )


def format_job_timing(intervals, verbose=False):
    """Runs of one job: timeline and acquisition duration (sum of the runs)"""
    if not intervals:
        return "no runs"
    if verbose:
        return format_all_intervals(intervals)
    acquisition = sum(i[1] - i[0] for i in intervals)
    return (
        f"{len(intervals)} runs, timeline {seconds(intervals[0][0])} to "
        f"{seconds(intervals[-1][1])} s, acquisition duration {seconds(acquisition)} s"
    )


def format_all_intervals(intervals):
    intervals_str = ", ".join(
        f"[{best_unit_time(i[0])}, {best_unit_time(i[1])}]" for i in intervals
    )
    return f"{intervals_str}  {len(intervals)} run(s)"


def print_jobs_status_summary(status_data, verbose=False):
    intervals = status_data.get("original_run_timing_intervals", [])
    print(f" Manifest file:      {status_data['manifest_path']}")
    print(f" Campaign dir:       {status_data['campaign_dir']}")
    print(f" Simulation ID:      {status_data['simulation_id']}")
    print(f" Created at:         {status_data['created_at']}")
    print(f" Split policy:       {status_data['policy']}")
    print(f" Prefer resolved:    {status_data.get('prefer_resolved_simulation', True)}")
    print(f" Number of jobs:     {status_data['number_of_jobs']}")
    print(f" Time intervals:     {format_campaign_timing(intervals, verbose)}")
    master_str = (
        "Found"
        if status_data["master_simulation_exists"]
        else colored.stylize("Missing", color_error)
    )
    print(f" Master simulation:  {master_str}")
    print(f"   Path:             {status_data['master_simulation_path']}")
    resolved_exists = status_data.get("resolved_simulation_exists", False)
    resolved_path = status_data.get("resolved_simulation_path")
    if resolved_path is not None:
        resolved_str = (
            "Found" if resolved_exists else colored.stylize("Missing", color_error)
        )
        print(f" Resolved sim:       {resolved_str}")
        print(f"   Path:             {resolved_path}")
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

    jobs = status_data["jobs"]
    inputs_size = sum(job.get("input_files_size_bytes", 0) for job in jobs)
    folders_size = sum(job.get("folder_size_bytes", 0) for job in jobs)
    # the input files are the same for all jobs (one copy or link per job)
    per_job = sorted({job.get("number_of_input_files", 0) for job in jobs})
    per_job_str = (
        str(per_job[0]) if len(per_job) == 1 else f"{per_job[0]} to {per_job[-1]}"
    )
    input_mode = (
        "links" if any(j.get("input_mode") == "linked" for j in jobs) else "copies"
    )
    print(
        f"  Inputs: {per_job_str} files per job ({input_mode}), "
        f"{format_bytes(inputs_size)} for all the jobs; "
        f"job folders: {format_bytes(folders_size)}"
    )

    for job in jobs:
        job_idx = job["job_index"]
        folder = job["folder_name"]
        st = job["status"].upper()
        st_str = colored.stylize(st, color_error) if st != "READY" else st
        exec_status = job.get("execution_status")
        exec_str = exec_status.upper() if exec_status is not None else "NONE"
        job_intervals = job.get("run_timing_intervals", [])
        timing_str = format_job_timing(job_intervals, verbose)
        print(
            f"  [Job {job_idx:04d}] {folder}: status = {st_str}, "
            f"execution = {exec_str}, {timing_str}"
        )
        input_check_error = job.get("input_check_error")
        if input_check_error is not None:
            err_msg = f"     Cannot check the input files: {input_check_error}"
            print(colored.stylize(err_msg, color_error))
        missing_files = job.get("missing_input_files", [])
        if missing_files:
            for missing in missing_files:
                err_msg = f"     Missing input file: {missing}"
                print(colored.stylize(err_msg, color_error))


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("campaign_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "-v", "--verbose", is_flag=True, help="Print all the run timing intervals"
)
def go(campaign_dir, verbose):
    """
    Print a status summary for an OpenGATE job split campaign given its folder.
    """
    status_data = jobs_status(campaign_dir)
    print_jobs_status_summary(status_data, verbose=verbose)


if __name__ == "__main__":
    go()

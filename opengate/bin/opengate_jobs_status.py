#!/usr/bin/env python3

import click
from opengate.jobs import get_jobs_status

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def print_jobs_status_summary(status_data, verbose=False):
    print(f" Manifest file:      {status_data['manifest_path']}")
    print(f" Root directory:     {status_data['split_root_folder']}")
    print(f" Simulation ID:      {status_data['simulation_id']}")
    print(f" Created at:         {status_data['created_at']}")
    print(f" Split policy:       {status_data['policy']}")
    print(f" Number of jobs:     {status_data['number_of_jobs']}")
    print(
        f" Master simulation:  {'Found' if status_data['master_simulation_exists'] else 'Missing'}"
    )
    print(" Job Status Summary:")
    counts = status_data["summary_counts"]
    print(
        f"  Total: {counts['total']}  |  Ready: {counts['ready']}  |  Completed: {counts['completed']}  |  Missing: {counts['missing_folder'] + counts['missing_metadata']}"
    )

    for job in status_data["jobs"]:
        job_idx = job["job_index"]
        folder = job["folder_name"]
        st = job["status"].upper()
        outputs = job["output_files"]
        out_str = (
            f" ({len(outputs)} output file(s): {', '.join(outputs[:3])}{'...' if len(outputs) > 3 else ''})"
            if outputs
            else ""
        )
        print(f"  [Job {job_idx:04d}] {folder}: status = {st}{out_str}")
        if verbose:
            print(f"     Run timing intervals: {job['run_timing_intervals']}")
            print(f"     Original run indices: {job['original_run_indices']}")
            print(
                f"     Folder exists: {job['folder_exists']}, Metadata: {job['metadata_exists']}, Sim: {job['simulation_exists']}"
            )


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

#!/usr/bin/env python3

from pathlib import Path

import click

from opengate.jobs import (
    DEFAULT_SIMULATION_FILENAME,
    DEFAULT_SPLIT_POLICY,
    jobs_split,
)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("campaign_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--number-of-jobs",
    type=int,
    required=True,
    help="Number of child jobs to create.",
)
@click.option(
    "--simulation-file",
    default=DEFAULT_SIMULATION_FILENAME,
    show_default=True,
    help="Name of the simulation JSON inside the campaign folder. Normally this should not be changed.",
)
@click.option(
    "--policy",
    default=DEFAULT_SPLIT_POLICY,
    show_default=True,
    type=click.Choice(["split_in_time_per_run", "split_in_time_total"]),
    help="Split policy to apply.",
)
@click.option(
    "--link-files/--copy-files",
    default=False,
    show_default=True,
    help="Link archived input files instead of copying them.",
)
@click.option(
    "--overwrite-existing-job-folders",
    is_flag=True,
    help="Allow overwriting an existing split campaign structure in the target folder.",
)
def go(
    campaign_dir,
    number_of_jobs,
    simulation_file,
    policy,
    link_files,
    overwrite_existing_job_folders,
):
    """Split the simulation found in CAMPAIGN_DIR into child job folders.

    The Python API returns a JobsSplitManager. The command-line tool prints the
    campaign folder path so shell workflows can pass it to later commands.
    """
    jobs_split_manager = jobs_split(
        simulation_folder=Path(campaign_dir),
        simulation_file=simulation_file,
        campaign_dir=Path(campaign_dir),
        number_of_jobs=number_of_jobs,
        policy=policy,
        link_files=link_files,
        overwrite_existing_job_folders=overwrite_existing_job_folders,
        write_resolved_simulation=True,
    )
    click.echo(str(jobs_split_manager.campaign_dir))


if __name__ == "__main__":
    go()

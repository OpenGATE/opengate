#!/usr/bin/env python3

import json
from pathlib import Path

import click

from opengate.jobs import jobs_clean_split

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("campaign_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--remove-job-folders/--keep-job-folders",
    default=True,
    show_default=True,
    help="Remove child job folders.",
)
@click.option(
    "--remove-metadata-files/--keep-metadata-files",
    default=True,
    show_default=True,
    help="Remove split-run-merge metadata files from the campaign folder.",
)
def go(
    campaign_dir,
    remove_job_folders,
    remove_metadata_files,
):
    """Remove temporary split-job artifacts from CAMPAIGN_DIR."""
    result = jobs_clean_split(
        Path(campaign_dir),
        remove_job_folders=remove_job_folders,
        remove_backend_status=remove_metadata_files,
        remove_execution_status=remove_metadata_files,
        remove_manifest=remove_metadata_files,
        remove_resolved_simulation=remove_metadata_files,
    )
    click.echo(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    go()

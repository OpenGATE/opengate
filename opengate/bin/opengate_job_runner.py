#!/usr/bin/env python3

from pathlib import Path

import click

from opengate.jobs import _run_job_folder_cli

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("job_folder", type=click.Path(exists=True, file_okay=False))
@click.option("--backend", default="local_cli", show_default=True)
def go(job_folder, backend):
    """Run one split-job folder from its persisted simulation.json and metadata."""
    result = _run_job_folder_cli(
        Path(job_folder),
        backend=backend,
        start_new_process=False,
    )
    if result["status"] != "completed":
        raise click.ClickException(result.get("error_message", "Job execution failed."))


if __name__ == "__main__":
    go()

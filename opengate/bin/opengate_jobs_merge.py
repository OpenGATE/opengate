#!/usr/bin/env python3

import json
from pathlib import Path

import click

from opengate.jobs import jobs_merge

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("campaign_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--to-path",
    type=click.Path(file_okay=False),
    default=None,
    help="Optional target output folder for the merged simulation. If omitted, the master simulation output_dir is used.",
)
def go(campaign_dir, to_path):
    """Merge a finished jobs campaign stored in CAMPAIGN_DIR."""
    merge_manager = jobs_merge(Path(campaign_dir), to_path=to_path, execute=True)
    merge_manager.print_merge_summary()
    click.echo(json.dumps(merge_manager.merge_result, indent=2, sort_keys=True))


if __name__ == "__main__":
    go()

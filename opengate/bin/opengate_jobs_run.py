#!/usr/bin/env python3

from pathlib import Path
import json

import click

from opengate.jobs import (
    DEFAULT_JOBS_BACKEND_OPTIONS_FILENAME,
    jobs_run,
)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def _load_backend_config(path):
    with open(path, "r") as input_file:
        config = json.load(input_file)
    if not isinstance(config, dict):
        raise click.ClickException(
            f"Backend options file '{path}' must contain a JSON object."
        )
    return config


def _resolve_backend_configuration(campaign_dir, backend, backend_options_json):
    campaign_dir = Path(campaign_dir)
    default_backend_options_path = campaign_dir / DEFAULT_JOBS_BACKEND_OPTIONS_FILENAME

    config = None
    if backend_options_json is not None:
        config = _load_backend_config(backend_options_json)
    elif default_backend_options_path.exists():
        config = _load_backend_config(default_backend_options_path)

    if backend is None:
        if config is not None:
            backend = config.get("backend")
        if backend is None:
            raise click.ClickException(
                "No backend was provided. Use --backend or provide "
                f"'{DEFAULT_JOBS_BACKEND_OPTIONS_FILENAME}' in the campaign folder."
            )
    elif config is not None and config.get("backend") not in (None, backend):
        click.echo(
            "Warning: backend from command line overrides backend declared in "
            f"'{backend_options_json or default_backend_options_path}'.",
            err=True,
        )

    resolved_backend_options = None
    if config is not None:
        resolved_backend_options = config.get("backend_options")

    return backend, resolved_backend_options


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("campaign_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--backend",
    default=None,
    help="Execution backend to use. If omitted, the command looks for jobs_backend_options.json in CAMPAIGN_DIR.",
)
@click.option(
    "--backend-options-json",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="JSON file containing backend configuration. If omitted, the command looks for jobs_backend_options.json in CAMPAIGN_DIR.",
)
@click.option(
    "--force-rerun-completed",
    is_flag=True,
    help="Rerun jobs already marked as completed.",
)
@click.option(
    "--allow-rerun-running",
    is_flag=True,
    help="Allow rerun of jobs currently marked as running.",
)
def go(
    campaign_dir,
    backend,
    backend_options_json,
    force_rerun_completed,
    allow_rerun_running,
):
    """Run a previously split jobs campaign stored in CAMPAIGN_DIR."""
    backend, backend_options = _resolve_backend_configuration(
        campaign_dir, backend, backend_options_json
    )
    result = jobs_run(
        Path(campaign_dir),
        backend=backend,
        backend_options=backend_options,
        force_rerun_completed=force_rerun_completed,
        allow_rerun_running=allow_rerun_running,
    )
    click.echo(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    go()

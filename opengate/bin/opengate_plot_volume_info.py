#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from opengate.geometry.volume_info import *
import json

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("json_file", type=click.Path(exists=True))
@click.option("--axis", "-a", default="all", help="all, XY or XZ or YZ")
@click.option("--hl", default=None, multiple=True, help="highlight volumes")
def go(json_file, axis, hl):
    # Load the JSON data
    with open(json_file, "r") as f:
        spect_data = json.load(f)

    # Plot in XY plane (2D view)
    if axis == "all":
        plot_all_views_2d(spect_data, show_labels=True, highlight_volumes=hl)
    else:
        plot_volume_boundaries_2d(
            spect_data, plane=axis, show_labels=True, highlight_volumes=hl
        )


if __name__ == "__main__":
    go()

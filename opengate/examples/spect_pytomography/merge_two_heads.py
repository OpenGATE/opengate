#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import SimpleITK as sitk
from opengate.contrib.spect.spect_helpers import merge_several_heads_projections

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("input_files", nargs=-1)
@click.option("--output", "-o", help="Output filename")
def go(input_files, output):

    output_img = merge_several_heads_projections(input_files)
    sitk.WriteImage(output_img, output)


if __name__ == "__main__":
    go()

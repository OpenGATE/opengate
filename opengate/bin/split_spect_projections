#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import itk
from opengate.image import split_spect_projections

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("inputs", nargs=-1)
@click.option("--ene", "-e", required=True, help="Number of energy windows")
@click.option("--output", "-o", required=True, help="output filename (.mhd)")
def go(inputs, ene, output):
    """
    Consider as input a set of images from a gate SPECT simulation.
    Each image is assumed to be several slices: one per energy windows times one per angle.
    The different images corresponds to several SPECT heads.

    The created output is on image per energy windows, with all angles (heads + rotations) as slices.
    """

    # compute the projections per energy window
    nb_ene = int(ene)
    outputs = split_spect_projections(inputs, nb_ene)

    # write images
    e = 0
    for o in outputs:
        f = output.replace(".mhd", f"_{e}.mhd")
        itk.imwrite(o, f)
        e += 1


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()

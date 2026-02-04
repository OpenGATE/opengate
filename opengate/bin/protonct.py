#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from opengate.contrib.protonct.protonct import protonct

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--output", "-o", default=None, help="output folder")
@click.option("--projections", "-p", default=720, help="number of projections")
@click.option("--protons-per-projection",
              "-n",
              default=1000,
              help="number of protons per projection")
@click.option("--seed", "-s", type=int, help="random number generator seed")
@click.option("--visu", is_flag=True, help="Enable visualization")
@click.option("--verbose", is_flag=True, help="verbose execution")
def go(output, projections, protons_per_projection, seed, visu, verbose):
    protonct(output, projections, protons_per_projection, seed, visu, verbose)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()

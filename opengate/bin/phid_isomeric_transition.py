#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.sources.phidsources import *
import click
import matplotlib.pyplot as plt

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("rad_name", nargs=1)
@click.option("--output", "-o", default=None, help="output file")
@click.option(
    "--verbose/--no-verbose", "-v", is_flag=True, default=False, help="Print data"
)
@click.option("--plot/--no-plot", is_flag=True, default=True, help="Plot data")
@click.option(
    "--log_scale", "--log", is_flag=True, default=False, help="plot with log scale"
)
def go(rad_name, output, verbose, plot, log_scale):
    """
    Display the isomeric gamma spectra for one given radionuclide.

    Data are retrieved from Geant4 database and can be checked with
    http://www.lnhb.fr/nuclear-data/module-lara/
    https://www-nds.iaea.org/relnsd/vcharthtml/VChartHTML.html
    By default, data are stored in text files in the folder: opengate/opengate/data/isomeric_transition
    """
    # FIXME dont work with some metasable state (Tc99m)

    # get nuclide
    nuclide = get_nuclide_from_name(rad_name)

    # load the isomeric transition data
    ene, weights = isomeric_transition_load(nuclide)

    # print
    keV = g4_units.keV
    if verbose:
        i = 0
        for e, w in zip(ene, weights):
            print(f"{i} Energy {e / keV:.3f} keV     {w * 100:.3f} %")
            i += 1
        print()

    # plot
    if plot:
        f, ax = plt.subplots(1, 1, figsize=(15, 5))
        ax.bar(
            ene / keV,
            height=weights * 100,
            width=0.4,
            label=f"{nuclide.nuclide}",
            log=log_scale,
        )
        ax.set_xlabel("Energy in keV")
        ax.set_ylabel("Intensity in %")
        ax.legend()
        if output:
            print(f"Output plot in {output}")
            f.savefig(output)
        else:
            plt.show()


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()

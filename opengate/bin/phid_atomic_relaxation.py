#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.sources.phidsources as phidsources
import click
import matplotlib.pyplot as plt

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("rad_name", nargs=1)
@click.option("--output", "-o", default=None, help="output plot in this file")
@click.option(
    "--verbose/--no-verbose", "-v", is_flag=True, default=False, help="Print data"
)
@click.option("--plot/--no-plot", is_flag=True, default=True, help="Plot data")
@click.option(
    "--iaea_web_site",
    is_flag=True,
    default=False,
    help="Force loading data from IAEA website and store to local file",
)
@click.option(
    "--from_data_file",
    default=None,
    help="Force loading data from the given file and store to local file",
)
@click.option(
    "--log_scale", "--log", is_flag=True, default=False, help="plot with log scale"
)
def go(rad_name, output, plot, verbose, log_scale, iaea_web_site, from_data_file):
    """
    Display the atomic relaxation photon spectra for one given radionuclide.

    Data are retrieved from https://www-nds.iaea.org/relnsd/vcharthtml/VChartHTML.html
    By default, data are stored in text files in the folder: opengate/opengate/data/atomic_relaxation
    """

    # get nuclide
    nuclide = phidsources.get_nuclide_from_name(rad_name)

    # load the atomic relaxation data
    if iaea_web_site and from_data_file is not None:
        gate.fatal(f"Use either --iaea_web_site or --from_data_file, not both")
    load_type = "local"
    if iaea_web_site:
        load_type = "iaea_web_site"
    if from_data_file:
        load_type = from_data_file
    ene, weights = phidsources.atomic_relaxation_load(nuclide, load_type)

    # print
    keV = gate.g4_units.keV
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
            width=0.2,
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

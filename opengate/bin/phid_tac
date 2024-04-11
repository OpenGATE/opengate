#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate.sources.phidsources as phidsources
import click
import radioactivedecay as rd
import matplotlib.pyplot as plt

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("rad_name", nargs=1)
@click.option("--output", "-o", default=None, help="output file")
@click.option(
    "--num",
    "-n",
    is_flag=True,
    default=False,
    help="Plot in nb of atoms instead of activity",
)
@click.option(
    "--timing",
    "-t",
    multiple=True,
    default=[2.0, 24.0, 5 * 24],
    help="timing (in hours)",
)
def go(rad_name, output, timing, num):
    # get nuclide, a, z
    nuclide = phidsources.get_nuclide_from_name(rad_name)
    hl = nuclide.half_life("h")

    # plot
    inv = rd.Inventory({nuclide.nuclide: 1.0}, "Bq")
    fig, ax = plt.subplots(ncols=len(timing), nrows=1, figsize=(5 * len(timing) + 5, 5))

    if len(timing) == 1:
        ax = [ax]
    i = 0
    yunits = "Bq"
    if num:
        yunits = "num"
    for t in timing:
        if hl < t:
            ax[i].hlines(y=0.5, xmin=0, xmax=hl, color="k", alpha=0.2)
            ax[i].vlines(x=hl, ymin=0, ymax=0.5, color="k", alpha=0.2)
        inv.plot(t, "h", yunits=yunits, fig=fig, axes=ax[i])
        i += 1
    plt.suptitle(f"{nuclide.nuclide}   half life = {nuclide.half_life('readable')}")

    if output:
        print(f"Output plot in {output}")
        fig.savefig(output)
    else:
        plt.show()


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()

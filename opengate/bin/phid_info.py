#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate.sources.phidsources as phid
import click
import matplotlib.pyplot as plt

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("rad_name", nargs=1)
@click.option("--output", "-o", default=None, help="output file")
def go(rad_name, output):
    nuclide = phid.print_phid_info(rad_name)
    print(nuclide)

    fig, ax = nuclide.plot(label_pos=0.66)
    if output:
        print(f"Output plot in {output}")
        fig.savefig(output)
    else:
        plt.show()


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()

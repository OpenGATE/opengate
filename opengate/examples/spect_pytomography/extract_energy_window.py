#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import SimpleITK as sitk
from opengate.examples.spect_pytomography.old.spect_helpers import extract_energy_window

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("input_files", nargs=-1)
@click.option(
    "--energy_window",
    "-e",
    default="all",
    help="Id of the energy windows to extract ('all' fr all)",
)
@click.option("--nb_of_energy_windows", default=3, help="Number of energy windows")
@click.option("--nb_of_gantries", "-g", default=60, help="Number of gantries")
def go(input_files, energy_window, nb_of_energy_windows, nb_of_gantries):
    energy_windows = [energy_window]

    img = sitk.ReadImage(input_files[0])
    size = img.GetSize()
    if size[2] != nb_of_energy_windows * nb_of_gantries:
        raise ValueError(
            f"Number of slices must be {nb_of_energy_windows}x{nb_of_gantries}="
            f"{nb_of_energy_windows * nb_of_gantries} while it is {size[2]}"
        )
    if energy_windows == ["all"]:
        energy_windows = range(0, int(size[2] / nb_of_gantries))
    else:
        energy_windows = [int(ene) for ene in energy_windows]

    # extract all ene window
    for ene in energy_windows:
        for input_file in input_files:
            img = sitk.ReadImage(input_file)
            img = extract_energy_window(img, ene, nb_of_energy_windows, nb_of_gantries)
            sitk.WriteImage(
                img,
                input_file.replace(".mhd", f"_ene_{ene}.mhd"),
            )


if __name__ == "__main__":
    go()

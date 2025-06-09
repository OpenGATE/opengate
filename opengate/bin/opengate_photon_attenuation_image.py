#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import itk

from opengate import g4_units
from opengate.contrib.dose.photon_attenuation_image_helpers import (
    create_photon_attenuation_image,
)
from opengate.image import resample_itk_image

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--image", "-i", required=True, type=str, help="Input image filename")
@click.option("--output", "-o", default="output.mhd", help="Output image filename")
@click.option(
    "--labels", "-l", required=True, type=str, help="Input label to material (json)"
)
@click.option("--energy", "-e", default=0.1405, help="Energy in MeV")
@click.option("--size", "-s", default=None, help="Attenuation image size")
@click.option("--spacing", default=None, help="Attenuation image spacing")
@click.option("--database", default="NIST", help="Database, NIST or EPDL")
@click.option(
    "--material_database",
    "--mdb",
    default=None,
    help="Gate material database (if needed)",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose output")
def go(
    image, labels, output, energy, size, spacing, material_database, database, verbose
):
    """
    This function processes an input image to generate an attenuation map based on provided specifications and parameters.
    The command-line interface (CLI) is used to specify options such as input image, output filename, labels, energy, size, spacing, and database type. Verbose mode can also be toggled for additional output information during execution.

    Parameters:
    - image: Input image filename (required).
    - output: Output image filename, defaults to 'output.mhd'.
    - labels: Input label to material from a JSON file (required).
    - energy: Energy in MeV, defaults to 0.1405.
    - size: Attenuation image size, default is (128, 128, 128) if not specified.
    - spacing: Attenuation image spacing, default is (4.42, 4.42, 4.42) if not specified.
    - database: Specifies the database to be used, either "NIST" or "EPDL". Default is "NIST".
    - verbose: Flag to toggle verbose output, defaults to False.

    The function performs the following operations:
    1. Reads the input image file.
    2. Resamples the image to the specified size and spacing.
    3. Writes the resampled image to the specified output file.
    4. Creates a simulation to compute the attenuation map.
    5. Adds an actor to the simulation to handle attenuation image processing.
    6. Configures the simulation parameters for attenuation calculation.
    7. Initiates the simulation to compute the mu-map.
    8. Outputs the completion of the process along with optional verbose logging.
    """

    # options
    image_filename = image
    labels_filename = labels
    if size is None:
        size = (128, 128, 128)
    if spacing is None:
        spacing = (4.42, 4.42, 4.42)

    # read image
    image = itk.imread(image_filename)

    # resample to the given size
    verbose and print("Resampling image ...")
    image = resample_itk_image(
        image, size, spacing, default_pixel_value=0, linear=False
    )
    itk.imwrite(image, output)

    # compute attenuation map (another sim)
    image = create_photon_attenuation_image(
        output,
        labels_filename,
        energy=energy * g4_units.MeV,
        material_database=material_database,
        database=database,
        verbose=verbose,
    )

    verbose and print(f"Finished computing mu in {output}")
    itk.imwrite(image, output)


if __name__ == "__main__":
    go()

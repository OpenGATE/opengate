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
@click.option("--labels", "-l", default=None, help="Input label to material (json)")
@click.option("--energy", "-e", default=0.1405, help="Energy in MeV")
@click.option(
    "--size",
    "-s",
    default=None,
    type=(float, float, float),
    help="Attenuation image size",
)
@click.option(
    "--spacing",
    default=None,
    type=(float, float, float),
    help="Attenuation image spacing",
)
@click.option("--database", default="NIST", help="Database, NIST or EPDL")
@click.option(
    "--material_database",
    "--mdb",
    default=None,
    help="Gate material database (if needed)",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose output")
@click.option(
    "--mm",
    is_flag=True,
    default=False,
    help="Change unit to mm^-1 instead of default cm^-1",
)
def go(
    image,
    labels,
    output,
    energy,
    size,
    spacing,
    material_database,
    database,
    verbose,
    mm,
):
    """
    This function processes an input image to generate an attenuation map based on provided specifications and parameters.

    Parameters:
    - image: Input image filename (required).
    - output: Output image filename, defaults to 'output.mhd'.
    - labels: Input label to material from a JSON file. If not provided: Schneider method.
    - energy: Energy in MeV, defaults to 0.1405.
    - size: Attenuation image size (if resample)
    - spacing: Attenuation image spacing  (if resample)
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

    # resample to the given size
    if size is not None and spacing is not None:
        verbose and print("Resampling image ...")
        # read image
        image = itk.imread(image_filename)
        image = resample_itk_image(
            image, size, spacing, default_pixel_value=-1000, linear=False
        )
        itk.imwrite(image, output)
        image_filename = output

    # compute attenuation map (another sim)
    image = create_photon_attenuation_image(
        image_filename,
        labels_filename,
        energy=energy * g4_units.MeV,
        material_database=material_database,
        database=database,
        verbose=verbose,
    )
    if mm:
        arr = itk.array_view_from_image(image)
        arr = arr / 10
        new_image = itk.image_from_array(arr)
        new_image.SetSpacing(image.GetSpacing())
        new_image.SetOrigin(image.GetOrigin())
        image = new_image

    verbose and print(f"Finished computing mu in {output}")
    itk.imwrite(image, output)


if __name__ == "__main__":
    go()

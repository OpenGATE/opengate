#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import itk
import opengate as gate
import opengate.contrib.phantoms.nemaiec as nemaiec
from opengate.image import resample_itk_image_like, create_3d_image, get_info_from_image
from opengate.utility import g4_units

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
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose output")
def go(image, labels, output, energy, size, spacing, database, verbose):
    """
    FIXME
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
    verbose and print("Starting resampling ...")
    like = create_3d_image(size, spacing)
    info1 = get_info_from_image(like)
    info2 = get_info_from_image(image)
    center1 = info1.size / 2.0 * info1.spacing + info1.origin - info1.spacing / 2.0
    center2 = info2.size / 2.0 * info2.spacing + info2.origin - info2.spacing / 2.0
    tr = center2 - center1
    # info1.origin = -(info1.size * info1.spacing) / 2.0 + info1.spacing / 2.0
    info1.origin = tr
    like.SetOrigin(info1.origin)
    image = resample_itk_image_like(image, like, default_pixel_value=0, linear=False)
    itk.imwrite(image, output)

    # compute attenuation map (another sim)
    sim = gate.Simulation()
    phantom, _ = nemaiec.add_iec_phantom_vox(sim, "phantom", output, labels_filename)

    # mu map actor (process at the first begin of run only)
    mumap = sim.add_actor("AttenuationImageActor", "mumap")
    mumap.image_volume = phantom
    mumap.output_filename = output
    mumap.energy = energy * g4_units.MeV
    mumap.database = database
    verbose and print(f"Energy is {mumap.energy/g4_units.keV} keV")
    verbose and print(f"Database is {mumap.database}")

    # go
    verbose and print("Starting computing mu ...")
    sim.run()

    verbose and print(f"Finished computing mu in {output}")


if __name__ == "__main__":
    go()

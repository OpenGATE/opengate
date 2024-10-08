#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import json
import itk
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate.managers import Simulation
from opengate.engines import SimulationEngine
from opengate.utility import g4_units, print_dic, fatal
from opengate.image import *

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--spacing", "-s", default=4, help="Spacing in mm")
@click.option("--output", "-o", required=True, help="output filename (.mhd)")
@click.option(
    "--output_source", default=None, help="output filename for vox source (.mhd)"
)
@click.option(
    "--activities",
    "-a",
    default=None,
    nargs=6,
    help="List of 6 activities for the 6 spheres: 10, 13, 17, 22, 28, 37",
)
@click.option(
    "--no_shell",
    is_flag=True,
    default=False,
    help="If set, do not consider the shell of the sphere (for high resolution)",
)
def go(output, spacing, output_source, activities, no_shell):
    # create the simulation
    sim = Simulation()

    # world
    m = g4_units.m
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # add a iec phantom
    # FIXME add param
    iec = gate_iec.add_iec_phantom(
        sim, sphere_starting_angle=False, toggle_sphere_order=False
    )

    # create an empty image with the size (extent) of the volume
    # add one pixel margin
    image = create_image_with_volume_extent(
        iec, spacing=[spacing, spacing, spacing], margin=1
    )
    info = get_info_from_image(image)
    print(f"Image size={info.size}")
    print(f"Image spacing={info.spacing}")
    print(f"Image origin={info.origin}")

    # voxelized a volume
    print("Starting voxelization ...")
    with SimulationEngine(sim) as se:
        labels, image = voxelize_volume(se, image)
    print(f"Output labels: ")
    print_dic(labels)

    # write labels
    lf = output.replace(".mhd", ".json")
    outfile = open(lf, "w")
    json.dump(labels, outfile, indent=4)

    # write image
    print(f"Write image {output}")
    itk.imwrite(image, output)

    # voxelized source ?
    if activities is not None:
        if output_source is None:
            fatal(f"Provide --output_source with --activities")
        spheres_diam = [10, 13, 17, 22, 28, 37]
        spheres_activity_concentration = activities
        # new data
        vox_img = create_image_like(image, allocate=True, pixel_type="float")
        arr = itk.array_view_from_image(vox_img)
        arr[:] = 0.0
        label_arr = itk.array_view_from_image(image)
        print()
        print(f"Voxelized source: ")
        for l in labels:
            label_index = labels[l]
            # consider iec_sphere_XXmm AND iec_sphere_shell_XXmm
            if l.startswith("iec_sphere_"):
                if no_shell and "shell" in l:
                    continue
                sph = int(l[-4:][:2])
                sph_index = spheres_diam.index(sph)
                arr[label_arr == label_index] = spheres_activity_concentration[
                    sph_index
                ]
                print(
                    f"Sphere {sph}mm : index = {label_index} "
                    f"-> {spheres_activity_concentration[sph_index]} BqmL"
                )
            # else:
            #    arr[label_arr == lab_index] = 0
            #    print(f"Unknown label {l}")
        print(f"Write image source {output_source}")
        itk.imwrite(vox_img, output_source)
    else:
        if output_source is not None:
            fatal(f"Provide --activities with --output_source")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import click
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate import logger
from opengate.managers import Simulation
from opengate.utility import g4_units
from opengate.image import *
from opengate.voxelize import write_voxelized_geometry, voxelized_source

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--spacing", "-s", default=4.0, help="Spacing in mm")
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
@click.option("--bg", default=0.0, help="Activity in the background")
@click.option("--cyl", default=0.0, help="Activity in the central cylinder")
@click.option(
    "--no_shell",
    is_flag=True,
    default=False,
    help="If set, do not consider the shell of the sphere (for high resolution)",
)
def go(output, spacing, output_source, activities, no_shell, bg, cyl):
    # create the simulation
    sim = Simulation()
    sim.verbose_level = logger.INFO

    # world
    m = g4_units.m
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # add a iec phantom
    iec = gate_iec.add_iec_phantom(
        sim, sphere_starting_angle=False, toggle_sphere_order=False
    )

    # voxelized the iec volume
    print("Starting voxelization ...")
    spacing = (spacing, spacing, spacing)
    volume_labels, image = sim.voxelize_geometry(extent=iec, spacing=spacing, margin=1)

    info = get_info_from_image(image)
    print(f"Image size={info.size}")
    print(f"Image spacing={info.spacing}")
    print(f"Image origin={info.origin}")

    # write files
    filenames = write_voxelized_geometry(sim, volume_labels, image, output)
    for f in filenames.values():
        print(f"Output: {f}")

    # voxelized source activities
    if activities is None:
        activities = [0.0] * 6
    a = {
        "iec_sphere_10mm": activities[0],
        "iec_sphere_13mm": activities[1],
        "iec_sphere_17mm": activities[2],
        "iec_sphere_22mm": activities[3],
        "iec_sphere_28mm": activities[4],
        "iec_sphere_37mm": activities[5],
        "iec_interior": bg,
        "iec_center_cylinder_hole": cyl,
    }
    if not no_shell:
        a["iec_sphere_shell_10mm"] = activities[0]
        a["iec_sphere_shell_13mm"] = activities[1]
        a["iec_sphere_shell_17mm"] = activities[2]
        a["iec_sphere_shell_22mm"] = activities[3]
        a["iec_sphere_shell_28mm"] = activities[4]
        a["iec_sphere_shell_37mm"] = activities[5]

    if output_source is not None:
        itk_source = voxelized_source(image, volume_labels, a)
        print(f"Write image source {output_source}")
        itk.imwrite(itk_source, output_source)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()

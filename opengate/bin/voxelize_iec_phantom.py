#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import click
from pathlib import Path
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
    help="If set, do not consider the shell of the sphere (for low resolution)",
)
@click.option(
    "--version",
    "iec_version",
    default=gate_iec.default_iec_version,
    type=click.Choice(list(gate_iec.iec_versions.keys())),
    help="Version of the IEC phantom (total length, walls, sphere z)",
)
@click.option(
    "--sphere_starting_angle",
    default=None,
    type=float,
    help="Angle (deg) of the first sphere (default 180 deg, the 37 mm sphere)",
)
@click.option(
    "--toggle_sphere_order",
    is_flag=True,
    default=False,
    help="Reverse the order of the spheres (the first one is the 10 mm sphere)",
)
@click.option(
    "--no_central_cylinder",
    is_flag=True,
    default=False,
    help="No central (lung) cylinder: its wall and its hole are water, with the "
    "background activity (--cyl is ignored)",
)
def go(
    output,
    spacing,
    output_source,
    activities,
    no_shell,
    bg,
    cyl,
    iec_version,
    sphere_starting_angle,
    toggle_sphere_order,
    no_central_cylinder,
):
    # create the simulation
    sim = Simulation()
    sim.verbose_level = logger.INFO

    # world
    m = g4_units.m
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # add a iec phantom
    deg = g4_units.deg
    iec = gate_iec.add_iec_phantom(
        sim,
        sphere_starting_angle=(
            False if sphere_starting_angle is None else sphere_starting_angle * deg
        ),
        toggle_sphere_order=toggle_sphere_order,
        version=iec_version,
    )

    # voxelized the iec volume
    print("Starting voxelization ...")
    spacing = (spacing, spacing, spacing)
    volume_labels, image = sim.voxelize_geometry(extent=iec, spacing=spacing, margin=1)

    info = get_info_from_image(image)
    print(f"Image size={info.size}")
    print(f"Image spacing={info.spacing}")
    print(f"Image origin={info.origin}")

    # no central cylinder: its volumes are water
    if no_central_cylinder:
        for v in ["iec_center_cylinder", "iec_center_cylinder_hole"]:
            volume_labels[v]["material"] = "G4_WATER"

    # write files (absolute path: the labels and the materials files are
    # otherwise written relative to the output folder of the simulation)
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output = str(output)
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
    if no_central_cylinder:
        a["iec_center_cylinder"] = bg
        a["iec_center_cylinder_hole"] = bg
    if not no_shell:
        a["iec_sphere_shell_10mm"] = activities[0]
        a["iec_sphere_shell_13mm"] = activities[1]
        a["iec_sphere_shell_17mm"] = activities[2]
        a["iec_sphere_shell_22mm"] = activities[3]
        a["iec_sphere_shell_28mm"] = activities[4]
        a["iec_sphere_shell_37mm"] = activities[5]

    if output_source is not None:
        itk_source = voxelized_source(image, volume_labels, a)
        Path(output_source).parent.mkdir(parents=True, exist_ok=True)
        print(f"Write image source {output_source}")
        itk.imwrite(itk_source, str(output_source))


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()

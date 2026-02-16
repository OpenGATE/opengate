#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from box import Box
import click
import matplotlib.pyplot as plt
import numpy as np
import opengate as gate
import pathlib
import pyvista
import SimpleITK as sitk
from opengate.filters.ast import FilterASTTransformer
import ast


current_path = pathlib.Path(__file__).parent.resolve()
data_path = current_path / "data"
output_path = current_path / "output"
output_file = output_path / "dose.mhd"

alpha_channel = -1
colors = Box(
    {
        "invisible": [0, 0, 0, 0],
        "red": [1, 0, 0, 1],
        "green": [0, 1, 0, 1],
        "blue": [0, 0, 1, 1],
        "cyan": [0, 1, 1, 1],
        "magenta": [1, 0, 1, 1],
        "yellow": [1, 1, 0, 1],
        "grey": [0.7, 0.7, 0.7, 1],
        "white": [1, 1, 1, 1],
        "pink": [1, 0.75, 0.79, 1],
        "orange": [1, 0.5, 0, 1],
    }
)


def simulation(n: int, visu=False):
    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    um = gate.g4_units.um
    MeV = gate.g4_units.MeV
    deg = gate.g4_units.deg

    tr = FilterASTTransformer()
    e = ast.parse("particle_name == 'proton'")
    e = tr.visit(e)
    print(ast.dump(e))

    # create the simulation
    sim = gate.Simulation()

    sim.progress_bar = True

    # main user options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = visu
    ui.visu_type = "vrml_file_only"
    ui.visu_filename = str(output_path / f"visu_{n}.wrl")
    ui.random_seed = "auto"
    ui.number_of_threads = 4

    # change world size
    world = sim.world
    world.size = [5 * m, 5 * m, 5 * m]
    world.color[alpha_channel] = 0

    # water box
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [31 * cm, 31 * cm, 31 * cm]
    waterbox.translation = [0 * mm, 0 * mm, 0 * mm]
    waterbox.material = "G4_WATER"
    waterbox.set_max_step_size(0.1 * mm)
    waterbox.color = colors.cyan

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("world", "gamma", 10 * m)
    sim.physics_manager.set_production_cut("world", "electron", 10 * m)
    sim.physics_manager.set_production_cut("world", "positron", 10 * m)

    if visu:
        sim.physics_manager.set_production_cut(waterbox.name, "gamma", 1 * mm)
        sim.physics_manager.set_production_cut(waterbox.name, "electron", 1 * mm)
        sim.physics_manager.set_production_cut(waterbox.name, "positron", 1 * mm)
    else:
        sim.physics_manager.set_production_cut(waterbox.name, "gamma", 1 * um)
        sim.physics_manager.set_production_cut(waterbox.name, "electron", 1 * um)
        sim.physics_manager.set_production_cut(waterbox.name, "positron", 1 * um)

    sim.physics_manager.set_user_limits_particles(["gamma", "electron"])

    # source
    source = sim.add_source("GenericSource", "beam")
    source.particle = "e-"
    source.energy.mono = 20 * MeV
    source.position.type = "point"
    source.position.translation = [0 * mm, 0 * mm, 1 * m + 15.5 * cm]
    source.direction.type = "iso"
    source.direction.theta = [0 * deg, 3 * deg]  # ZOX plane
    source.direction.phi = [0 * deg, 360 * deg]  # YOX plane
    source.n = n / ui.number_of_threads

    # dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = waterbox
    dose.output_filename = output_file
    dose.size = [31, 31, 155]
    dose.spacing = [1 * cm, 1 * cm, 2 * mm]
    dose.hit_type = "random"
    dose.dose.active = True
    dose.dose_uncertainty.active = True

    fp = sim.add_filter("ParticleFilter", "fp")
    fp.particle = "gamma"

    # dose.filters.append(fp)

    # dose.filter = "5 == 0"
    dose.filter = "particle_name == 'gamma' and 5 == 5 or 2 * pre_kinetic_energy < 20 * MeV and dbgp((pre_kinetic_energy - post_kinetic_energy) / step_length)"
    # dose.filter = "particle_name == 'gamma'"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # print results at the end
    print(stats)


def analysis():
    img = sitk.ReadImage(str(output_file).replace(".mhd", "_dose.mhd"))
    data = np.array(sitk.GetArrayFromImage(img))
    profile = [np.sum(plan) for plan in data]
    profile = profile[::-1]  # reverse order
    profile = profile[: len(profile) // 2]

    # Dose profile figure
    fig, ax = plt.subplots(figsize=(5.5, 3.8), dpi=300)
    plt.title("Depth dose profile")
    ax.set_xlabel("Depth (voxel)")
    ax.set_ylabel("Dose (Gy)")

    ax.plot(profile)

    fig.savefig("depth_dose_profile.png")
    plt.show()
    plt.close(fig)


def visualisation(n: int):
    pl = pyvista.Plotter()
    pl.import_vrml(str(output_path / f"visu_{n}.wrl"))
    pl.add_axes(line_width=5, color="white")
    pl.background_color = "black"
    for actor in pl.renderer.GetActors():
        actor.GetProperty().SetOpacity(0.7)
    pl.show()


@click.command()
@click.option(
    "-s",
    "--sim",
    "--simulation",
    "enable_sim",
    is_flag=True,
    default=False,
    help="enable simulation",
)
@click.option(
    "-a",
    "--analysis",
    "enable_analysis",
    is_flag=True,
    default=False,
    help="enable analysis",
)
@click.option(
    "-V",
    "--visu",
    "--visualisation",
    "enable_visu",
    is_flag=True,
    default=False,
    help="enable visualisation",
)
@click.option(
    "-n", "--primaries", "n", type=str, default="1e2", help="number of primaries"
)
def main(enable_sim: bool, enable_analysis: bool, enable_visu: bool, n: str):
    n = int(float(n))  # handle scientific notation

    if enable_sim:
        simulation(n, visu=enable_visu)

    if enable_analysis:
        analysis()

    if enable_visu:
        visualisation(n)


if __name__ == "__main__":
    main()

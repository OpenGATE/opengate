#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.actors.digitizers import *
import numpy as np
import uproot
import itk
from pathlib import Path
import pandas as pd


def std_dev_img_calculation(N, sum_E, squared_sum_E):
    return np.sqrt((1 / (N - 1)) * ((squared_sum_E / N) - (sum_E / N) ** 2))


def img_opening(img_to_open):
    img = itk.imread(img_to_open)
    img = itk.GetArrayFromImage(img)
    numpy_column_order = [2, 1, 0]
    img = np.transpose(img, numpy_column_order)
    img = img.reshape((img.shape[0], img.shape[1]))
    img = img.transpose()
    return img


def img_generation_from_phsp(
    nb_pixel_x, nb_pixel_y, dim_x, dim_y, df, type="E", process=None
):
    x_edges = np.linspace(-dim_x / 2, dim_x / 2, nb_pixel_x + 1)
    y_edges = np.linspace(-dim_y / 2, dim_y / 2, nb_pixel_y + 1)
    spacing = np.array([x_edges[1] - x_edges[0], y_edges[1] - y_edges[0]])
    origin = np.array([x_edges[0], y_edges[0]])
    if process == "rayleigh":
        process = "Rayl"
    if process == "compton":
        process = "compt"
    if process != None:
        if process != "secondaries" and process != "primaries":
            df = df[df["LastOccuringProcess__water"] == process].copy()
        elif process == "secondaries":
            df = df[df["LastOccuringProcess__water"] != "Transportation"].copy()
        elif process == "primaries":
            df = df[df["LastOccuringProcess__water"] == "Transportation"].copy()

    df[["PrePositionLocal_X", "PrePositionLocal_Y"]] = (
        df[["PrePositionLocal_X", "PrePositionLocal_Y"]] - origin
    ) / spacing
    df[["PrePositionLocal_X", "PrePositionLocal_Y"]] = df[
        ["PrePositionLocal_X", "PrePositionLocal_Y"]
    ].astype(int)
    if type == "energy":
        df["KineticEnergy"] = df["KineticEnergy"] * df["Weight"]
    elif type == "counts":
        df["KineticEnergy"] = df["Weight"]

    df_merge_evt = (
        df.groupby(["EventID", "PrePositionLocal_X", "PrePositionLocal_Y"])
        .agg(KineticEnergy=("KineticEnergy", "sum"))
        .reset_index()
    )
    size = int(df_merge_evt.size / 4)
    df_merge_evt[["PrePositionLocal_X", "PrePositionLocal_Y"]] = (
        df_merge_evt[["PrePositionLocal_X", "PrePositionLocal_Y"]].astype(float)
        + np.random.random(size=(size, 2))
    ) * spacing + origin
    df_squared = df_merge_evt.copy()
    df_squared["KineticEnergy"] = df_squared["KineticEnergy"] ** 2

    H, _, _ = np.histogram2d(
        df_merge_evt["PrePositionLocal_Y"],
        df_merge_evt["PrePositionLocal_X"],
        bins=[x_edges, y_edges],
        weights=df_merge_evt["KineticEnergy"],
    )
    H2, _, _ = np.histogram2d(
        df_squared["PrePositionLocal_Y"],
        df_squared["PrePositionLocal_X"],
        bins=[x_edges, y_edges],
        weights=df_squared["KineticEnergy"],
    )

    return H, H2


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test099_fluence_actor", "test099"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    # sim.visu = True
    sim.random_seed = 123456
    sim.output_dir = paths.output
    sim.progress_bar = True
    ui = sim.user_info
    # ui.running_verbose_level = gate.logger.EVENT

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    #  change world size
    world = sim.world
    world.material = "G4_Galactic"
    world.size = [0.5 * m, 0.5 * m, 0.5 * m]

    # waterbox
    fluence_plane = sim.add_volume("Box", "air_plane")
    fluence_plane.size = [10 * cm, 10 * cm, 1 * nm]
    fluence_plane.material = "G4_Galactic"
    fluence_plane.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1000 * m

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.type = "gauss"
    source.energy.mono = 0.5 * MeV
    source.energy.sigma_gauss = 0.2 * MeV
    source.particle = "gamma"
    source.position.type = "disc"
    source.position.radius = 1 * cm
    source.position.translation = [0, 0, -80 * mm]
    source.direction.type = "iso"
    source.n = 100000

    water_box = sim.add_volume("Box", "water")
    water_box.size = [15 * cm, 15 * cm, 5 * cm]
    water_box.material = "G4_WATER"
    water_box.translation = [0, 0, -30 * mm]

    # add fluence actor
    fluence_actor = sim.add_actor("FluenceActor", "fluence_actor")
    fluence_actor.score_by_process = True
    # let the actor score other quantities additional to edep (default)
    fluence_actor.counts_uncertainty.active = True
    fluence_actor.counts_squared.active = True
    fluence_actor.energy.active = True
    fluence_actor.energy_uncertainty.active = True
    fluence_actor.energy_squared.active = True
    fluence_actor.output_filename = "test099_processes.mhd"
    fluence_actor.attached_to = fluence_plane
    fluence_actor.size = [10, 10, 1]
    mm = gate.g4_units.mm
    ts = [10 * cm, 10 * cm, 1 * nm]
    fluence_actor.spacing = [x / y for x, y in zip(ts, fluence_actor.size)]
    fluence_actor.hit_type = "random"

    ##add phase space actor
    att = LastProcessDefinedStepInVolumeAttribute(sim, water_box.name)

    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = fluence_plane.name
    phsp.attributes = [
        "KineticEnergy",
        "EventID",
        "Weight",
        "PrePositionLocal",
        "ParticleName",
    ]
    phsp.attributes.append(att.name)
    phsp.output_filename = f"test099_processes.root"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # start simulation
    sim.run(start_new_process=False)
    print(stats)
    p = Path(sim.output_dir)

    with uproot.open(p / phsp.output_filename) as root_file:
        df = root_file["PhaseSpace"].arrays(library="pd")

    processes = ["rayleigh", "compton", "secondaries", "primaries"]
    types = ["counts", "energy"]
    dict_comp = {}
    for process in processes:
        for type in types:
            string = f"{process}_{type}"
            print(f"Processing {string}")
            img_fluence = img_opening(p / f"test099_processes_{type}_{process}.mhd")
            img_squared_fluence = img_opening(
                p / f"test099_processes_{type}_squared_{process}.mhd"
            )
            img_uncertainty_fluence = img_opening(
                p / f"test099_processes_{type}_uncertainty_{process}.mhd"
            )
            img_phsp, img_squared_phsp = img_generation_from_phsp(
                fluence_actor.size[0],
                fluence_actor.size[1],
                fluence_plane.size[0],
                fluence_plane.size[1],
                df.copy(),
                type=type,
                process=process,
            )
            std_dev_phsp = std_dev_img_calculation(source.n, img_phsp, img_squared_phsp)
            img_uncertainty_phsp = np.divide(
                std_dev_phsp,
                (img_phsp / source.n),
                out=np.zeros_like(std_dev_phsp),
                where=(img_phsp != 0),
            )
            dict_comp[f"{string}"] = [img_fluence, img_phsp]
            dict_comp[f"{string}_squared"] = [img_squared_fluence, img_squared_phsp]
            dict_comp[f"{string}_uncertainty"] = [
                img_uncertainty_fluence,
                img_uncertainty_phsp,
            ]

    l_bool = []
    for key, elem in dict_comp.items():
        diff = np.round((elem[0] - elem[1]), 4)
        is_ok = np.all(diff == 0)
        l_bool.append(is_ok)

    l_bool = np.array(l_bool, dtype="bool")
    is_ok = np.all(l_bool)
    if not is_ok:
        print("Some processes did not match.")
        print(diff, l_bool)
    utility.test_ok(is_ok)

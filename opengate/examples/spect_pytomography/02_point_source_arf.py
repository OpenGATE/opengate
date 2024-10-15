#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect.ge_discovery_nm670 as nm670
from pathlib import Path
import SimpleITK as sitk

from opengate.contrib.spect.ge_discovery_nm670 import add_arf_detector
from opengate.contrib.spect.spect_helpers import (
    merge_several_heads_projections,
    extract_energy_window_from_projection_actors,
)
from opengate.examples.spect_pytomography.helpers import add_point_source

if __name__ == "__main__":

    # create the simulation
    sim = gate.Simulation()

    # main options
    # sim.visu = True # uncomment to enable visualisation
    sim.visu_type = "qt"
    # sim.visu_type = "vrml"
    sim.random_seed = "auto"
    sim.number_of_threads = 1
    sim.progress_bar = True
    sim.output_dir = Path("output") / "02_point_source_arf"
    if sim.visu:
        sim.number_of_threads = 1

    # units
    sec = gate.g4_units.s
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    Bq = gate.g4_units.Bq

    # options
    activity = 2e5 * Bq / sim.number_of_threads
    n = 60
    total_time = 20 * sec
    radius = 16 * cm

    # visu
    if sim.visu:
        total_time = 1 * sec
        sim.number_of_threads = 1
        activity = 100 * Bq

    # world
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "G4_AIR"

    # set the two spect heads
    spacing = [2.21 * mm * 2, 2.21 * mm * 2]
    size = [128, 128]
    pth = Path("pth") / "arf_034_nm670_tc99m.pth"
    det_plane1, arf1 = add_arf_detector(
        sim, radius, 0, size, spacing, "lehr", "detector", 1, pth
    )
    det_plane2, arf2 = add_arf_detector(
        sim, radius, 180, size, spacing, "lehr", "detector", 2, pth
    )
    det_planes = [det_plane1, det_plane2]
    arfs = [arf1, arf2]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 100 * mm)

    # add point source
    source = add_point_source(sim, "src", det_planes, "tc99m", activity)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = f"stats.txt"

    # set the rotation angles (runs)
    step_time = total_time / n
    sim.run_timing_intervals = [[i * step_time, (i + 1) * step_time] for i in range(n)]

    # compute the gantry rotations
    step_angle = 180 / n
    nm670.rotate_gantry(det_plane1, radius, 0, step_angle, n)
    nm670.rotate_gantry(det_plane2, radius, 180, step_angle, n)

    # options to make it faster, but unsure if the geometry is correct
    sim.dyn_geom_open_close = False
    sim.dyn_geom_optimise = False

    # go
    sim.run()

    # print
    print(stats)

    # extract energy window images
    energy_window = 1
    filenames = extract_energy_window_from_projection_actors(
        arfs, energy_window=energy_window, nb_of_energy_windows=2, nb_of_gantries=n
    )

    # merge two heads
    output_img = merge_several_heads_projections(filenames)
    sitk.WriteImage(output_img, sim.output_dir / f"projections_ene_{energy_window}.mhd")

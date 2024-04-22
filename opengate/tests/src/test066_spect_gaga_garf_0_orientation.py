#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test066_spect_gaga_garf_helpers import *
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test066")
    output_path = paths.output

    # create the simulation
    sim = gate.Simulation()
    simu_name = "test066_0_orientation"

    # options
    ui = sim.user_info
    ui.number_of_threads = 1
    ui.visu = True
    ui.visu_type = "vrml"
    ui.random_seed = "auto"
    ui.check_volumes_overlap = True

    # units
    mm = gate.g4_units.mm
    sec = gate.g4_units.second
    Bq = gate.g4_units.Bq
    cm3 = gate.g4_units.cm3
    BqmL = Bq / cm3

    # options
    colli_type = "lehr"
    radius = 400 * mm
    gantry_angle = -20

    # main elements : spect + phantom
    head, crystal = genm670.add_spect_head(sim, collimator_type=colli_type, debug=True)

    # rotation by default
    genm670.set_head_orientation(head, colli_type, radius, gantry_angle)
    print(f"Head translation = {head.translation[0]=:.2f}")

    # add arf plane (put in parallel world to avoid overlap)
    sim.add_parallel_world("arf_world")
    size = [128, 128]
    size = [198, 158]  # enlarged to see better
    spacing = [4 * mm, 4 * mm]
    plane_size = [size[0] * spacing[0], size[1] * spacing[1]]
    arf_plane = genm670.add_detection_plane_for_arf(
        sim, plane_size, colli_type, radius, gantry_angle
    )
    arf_plane.mother = "arf_world"
    print(f"Plane translation =  {arf_plane.translation[0]:.2f}")

    # table
    genm670.add_fake_table(sim)

    # add IEC phantom
    gate_iec.add_iec_phantom(sim, name="iec")
    sim.physics_manager.set_production_cut("iec", "all", 1 * mm)

    # run
    sim.run()

    # colors
    red = [1, 0.7, 0.7, 0.8]
    blue = [0.5, 0.5, 1, 0.8]
    gray = [0.5, 0.5, 0.5, 1]
    white = [1, 1, 1, 1]
    yellow = [1, 1, 0, 1]
    green = [0, 1, 0, 1]

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import os

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "gate_test004_simulation_stats_actor")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = True
    ui.visu_type = "vrml_file_only"
    ui.visu_filename = "geant4VisuFile.wrl"
    ui.visu_verbose = False
    ui.number_of_threads = 1
    ui.random_engine = "MersenneTwister"
    ui.random_seed = "auto"

    # set the world size like in the Gate macro
    m = gate.g4_units("m")
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]

    # add a simple waterbox volume
    waterbox = sim.add_volume("Box", "Waterbox")
    cm = gate.g4_units("cm")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    # default source for tests
    keV = gate.g4_units("keV")
    mm = gate.g4_units("mm")
    Bq = gate.g4_units("Bq")
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    # source.activity = 200000 * Bq
    source.activity = 200 * Bq

    # runs
    sec = gate.g4_units("second")
    sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1.0 * sec]]

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # start simulation
    # sim.apply_g4_command("/run/verbose 1")
    sim.run(True)

    # visu
    try:
        import pyvista
    except:
        print(
            "The module pyvista is not installed to be able to visualize vrml files. Execute:"
        )
        print("pip install pyvista")

    pl = pyvista.Plotter()
    pl.import_vrml(ui.visu_filename)
    pl.background_color = "black"
    axes = pyvista.Axes()
    axes.axes_actor.total_length = 1000  # mm
    axes.axes_actor.shaft_type = axes.axes_actor.ShaftType.CYLINDER
    axes.axes_actor.cylinder_radius = 0.01
    axes.axes_actor.x_axis_shaft_properties.color = (1, 0, 0)
    axes.axes_actor.x_axis_tip_properties.color = (1, 0, 0)
    axes.axes_actor.y_axis_shaft_properties.color = (0, 1, 0)
    axes.axes_actor.y_axis_tip_properties.color = (0, 1, 0)
    axes.axes_actor.z_axis_shaft_properties.color = (0, 0, 1)
    axes.axes_actor.z_axis_tip_properties.color = (0, 0, 1)
    pl.add_actor(axes.axes_actor)
    # pl.add_axes_at_origin()
    pl.show()

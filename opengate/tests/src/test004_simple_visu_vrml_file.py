#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.tests.utility as utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test004_simulation_stats_actor"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = True
    sim.visu_type = "vrml_file_only"
    sim.visu_filename = "geant4VisuFile.wrl"
    sim.visu_verbose = False
    sim.number_of_threads = 1
    sim.random_engine = "MersenneTwister"
    sim.random_seed = "auto"

    # set the world size like in the Gate macro
    m = gate.g4_units.m
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]

    # add a simple waterbox volume
    waterbox = sim.add_volume("Box", "Waterbox")
    cm = gate.g4_units.cm
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    # default source for tests
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    # source.activity = 200000 * Bq
    source.activity = 200 * Bq

    # runs
    sec = gate.g4_units.second
    sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1.0 * sec]]

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # start simulation
    # sim.g4_commands_after_init.append("/run/verbose 1")
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
    pl.import_vrml(sim.visu_filename)
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

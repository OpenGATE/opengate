#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    # paths = utility.get_default_test_paths(__file__, "gate_test010_generic_source")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = True
    sim.visu_type = "vrml"
    sim.number_of_threads = 1

    # useful units
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    deg = gate.g4_units.deg
    mm = gate.g4_units.mm
    m = gate.g4_units.m
    cm = gate.g4_units.cm

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # add a simple volume
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
    waterbox.material = "G4_AIR"

    # source box
    b = sim.add_volume("Box", "sourcebox")
    b.size = [5 * cm, 5 * cm, 5 * cm]
    b.translation = [0 * cm, 50 * cm, 0 * cm]
    r = Rotation.from_euler("y", -25, degrees=True)
    r = r * Rotation.from_euler("x", -35, degrees=True)
    b.rotation = r.as_matrix()

    # source
    source = sim.add_source("GenericSource", "source1")
    source.mother = "sourcebox"
    source.particle = "gamma"
    source.n = 50
    source.position.type = "disc"
    source.position.radius = 0 * mm
    source.direction_relative_to_volume = True
    source.direction.type = "iso"
    source.direction.focus_point = [1 * cm, 2 * cm, 3 * cm]
    source.direction.theta = [0 * deg, 10 * deg]
    source.direction.phi = [0 * deg, 360 * deg]

    source.energy.type = "mono"
    source.energy.mono = 100 * MeV

    # actors
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")

    # start simulation
    sim.run()

    # get results
    stats = sim.output.get_actor("Stats")
    print(stats)

    utility.test_ok(False)

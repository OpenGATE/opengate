#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import pathlib

# add a PET ... or two PET !
import opengate.contrib.pet.philipsvereos as gate_pet

if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.check_volumes_overlap = False

    #  change world size
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]

    # add a box (not really useful here)
    # prefer air to speed simulation
    airbox = sim.add_volume("Box", "Airbox")
    airbox.size = [30 * cm, 30 * cm, 30 * cm]
    airbox.translation = [0 * cm, 0 * cm, 0 * cm]
    airbox.material = "G4_AIR"
    airbox.color = [0, 0, 1, 1]  # blue

    pet1 = gate_pet.add_pet(sim, "pet1")
    # pet2 = gate_vereos.add_pet(sim, 'pet2')
    # pet2.translation = [0, 0, pet1.dz * 2]

    # default source for tests
    source = sim.add_source("GenericSource", "Default")
    Bq = gate.g4_units.Bq
    source.particle = "e+"
    source.energy.type = "F18"
    source.position.type = "sphere"
    source.position.radius = 5 * cm
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.activity = 1000 * Bq

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # start simulation
    sim.run()

    # print results
    stats = sim.output.get_actor("Stats")
    # stats.write('output_ref/test018_stats_ref.txt')

    # check
    stats = sim.output.get_actor("Stats")
    stats_ref = utility.read_stat_file(
        pathFile / ".." / "data" / "output_ref" / "test018_stats_ref.txt"
    )
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.15)

    utility.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate import g4_units
import opengate.contrib.pet.philipsvereos as pet_vereos
from opengate.geometry.utility import get_grid_repetition

if __name__ == "__main__":
    # initialize the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 8

    # world
    m = g4_units.m
    sim.world.size = [3 * m, 3 * m, 3 * m]
    sim.world.material = "G4_AIR"

    # waterbox
    cm = g4_units.cm
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [10 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    # insert a TEP
    pet = pet_vereos.add_pet(sim, "pet")

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1 * m)
    sim.physics_manager.set_production_cut("waterbox", "gamma", 0.1 * cm)

    # source
    MBq = 1e6 * g4_units.Bq
    source = sim.add_source("GenericSource", "source")
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.particle = "e+"
    source.energy.type = "F18"
    source.direction.type = "iso"
    source.activity = 300 * MBq

    # repeat crystal
    crystal = sim.add_volume("Box", "crystal")
    crystal.size = [1 * cm, 1 * cm, 1 * cm]
    crystal.translation = get_grid_repetition([2, 3, 4], [0.5 * cm, 0.5 * cm, 0.5 * cm])

    # go
    sim.run()

    # get results
    output = sim.output

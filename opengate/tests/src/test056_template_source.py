#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    """
    Example to create a new type of source.

    You should copy-paste the following files, changing their name and
    adapting their content to your needs.

    Python side (user parameters):
    - opengate/source/TemplateSource.py

    CPP side (core)
    - core/opengate_core/opengate_lib/GateTemplateSource.h
    - core/opengate_core/opengate_lib/GateTemplateSource.cpp
    - core/opengate_core/opengate_lib/pyGateTemplateSource.cpp

    And modify the following files:
    - opengate/source/helpers_source.py
        => to add MySource in the 'source_type_names' list
    - core/opengate_core/opengate_core.cpp
        => to add definition and call of 'init_GateMySourceSource'

    """

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    # ui.running_verbose_level = gate.EVENT
    ui.visu = False
    ui.number_of_threads = 1

    # g4 units
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [200 * cm, 200 * cm, 200 * cm]

    # add a simple volume
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [4 * cm, -3 * cm, 2 * cm]
    waterbox.material = "G4_WATER"

    # test sources
    source = sim.add_source("TemplateSource", "source")
    source.mother = waterbox.name
    source.float_value = 1234 * MeV
    source.vector_value = [1 * cm, 2 * cm, 3 * cm]
    source.n = 666 / ui.number_of_threads

    # actors
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # start simulation
    output = sim.start()

    # get results
    stats = output.get_actor("Stats")
    print(stats)

    is_ok = stats.counts.event_count = 666
    utility.test_ok(is_ok)

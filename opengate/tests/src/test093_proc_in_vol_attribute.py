#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests.utility import get_default_test_paths, test_ok, print_test
from opengate.utility import g4_units
from opengate.logger import INFO, DEBUG, RUN, NONE
from opengate.managers import Simulation


if __name__ == "__main__":
    paths = get_default_test_paths(__file__, None, "test093")

    # units
    m = g4_units.m
    mm = g4_units.mm
    cm = g4_units.cm
    keV = g4_units.keV

    # simulation
    sim = Simulation()
    sim.progress_bar = True
    sim.visu = True
    sim.visu_type = "qt"
    sim.output_dir = paths.output

    # add a volume
    waterbox1 = sim.add_volume("Box", "Waterbox1")
    waterbox1.size = [20 * cm, 20 * cm, 10 * cm]
    waterbox1.translation = [0 * cm, 0 * cm, 0 * cm]
    waterbox1.material = "G4_WATER"

    # add a volume
    waterbox2 = sim.add_volume("Box", "Waterbox2")
    waterbox2.size = [20 * cm, 20 * cm, 10 * cm]
    waterbox2.translation = [0 * cm, 0 * cm, -10 * cm]
    waterbox2.material = "G4_WATER"

    # add a "detector"
    detector = sim.add_volume("Box", "detector")
    detector.size = [50 * cm, 50 * cm, 1 * cm]
    detector.translation = [0 * cm, 0 * cm, 20 * cm]
    detector.material = "G4_LEAD_OXIDE"

    # source
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 100 * keV
    source.position.type = "sphere"
    source.position.radius = 20 * mm
    source.position.translation = [0 * cm, 0 * cm, -30 * cm]
    source.direction.type = "focused"
    source.direction.focus_point = [0 * cm, 0 * cm, -25 * cm]
    source.direction.momentum = [0, 0, -1]
    source.n = 2000

    # add a stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # phsp
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = detector

    phsp.attributes = ["KineticEnergy", "PrePosition"]
    # at1 = Attribute("ProcessDefinedStep", "Compton", waterbox.name)
    # at2 = Attribute("ProcessDefinedStep", "Rayley", waterbox.name)
    # at3 = Attribute("ProcessDefinedStep", "Rayley", waterbox.name)
    # phsp.attributes = ["KineticEnergy", "PrePosition", at1, at2, at3]

    phsp.output_filename = "phsp.root"
    phsp.steps_to_store = "entering"

    # hits collection

    # go
    sim.run()
    print(stats)

    is_ok = False
    test_ok(is_ok)

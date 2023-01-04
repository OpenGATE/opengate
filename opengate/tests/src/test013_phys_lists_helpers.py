#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4


def create_pl_sim():
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = True
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_engine = "MersenneTwister"
    ui.random_seed = 123456987

    # set the world size like in the Gate macro
    m = gate.g4_units("m")
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]

    # add a simple waterbox volume
    waterbox = sim.add_volume("Box", "waterbox")
    cm = gate.g4_units("cm")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    # add a daughter (in wb)
    b1 = sim.add_volume("Box", "b1")
    b1.mother = "waterbox"
    b1.size = [4 * cm, 4 * cm, 4 * cm]
    b1.translation = [5 * cm, 5 * cm, 0 * cm]
    b1.material = "G4_Pd"

    # add another box (in world)
    b2 = sim.add_volume("Box", "b2")
    b2.size = [4 * cm, 4 * cm, 4 * cm]
    b2.translation = [0 * cm, 0 * cm, 0 * cm]
    b2.material = "G4_LUNG_ICRP"

    # physics
    mm = gate.g4_units("mm")
    eV = gate.g4_units("eV")
    MeV = gate.g4_units("MeV")
    p = sim.get_physics_user_info()
    p.energy_range_min = 250 * eV
    p.energy_range_max = 15 * MeV

    # print info about physics
    print("Phys list:", p)
    # print("Phys list param:")
    # print(p.g4_em_parameters.ToString()) # no more available before init
    print("Available phys lists:")
    print(sim.physics_manager.dump_available_physics_lists())

    # default source for tests
    MeV = gate.g4_units("MeV")
    Bq = gate.g4_units("Bq")

    source = sim.add_source("Generic", "gamma")
    source.particle = "gamma"
    source.energy.mono = 10 * MeV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 10000 * Bq

    source = sim.add_source("Generic", "ion1")
    source.particle = "ion 9 18"  # or F18 or Fluorine18
    source.position.type = "sphere"
    source.position.translation = [10 * mm, 10 * mm, 20 * mm]
    source.position.radius = 3 * mm
    source.direction.type = "iso"
    source.activity = 2000 * Bq

    source = sim.add_source("Generic", "ion2")
    source.particle = "ion 53 124"  # 53 124 0 0       # Iodine 124
    source.position.type = "sphere"
    source.position.translation = [-10 * mm, -10 * mm, -40 * mm]
    source.position.radius = 1 * mm
    source.direction.type = "iso"
    source.activity = 2000 * Bq

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    return sim


def phys_em_parameters(p):
    # must be done after the initialization
    em = g4.G4EmParameters.Instance()  # p.g4_em_parameters
    em.SetFluo(True)
    em.SetAuger(True)
    em.SetAugerCascade(True)
    em.SetPixe(True)
    em.SetDeexcitationIgnoreCut(True)

    # is this needed to do like Gate ? (unsure)
    em.SetDeexActiveRegion("world", True, True, True)
    # em.SetDeexActiveRegion("waterbox", True, True, True)
    # em.SetDeexActiveRegion("b1", True, True, True)
    # em.SetDeexActiveRegion("b2", True, True, True)

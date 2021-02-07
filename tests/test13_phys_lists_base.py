#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam


def create_pl_sim():
    # verbose level
    gam.log.setLevel(gam.INFO)

    # create the simulation
    sim = gam.Simulation()

    # main options
    sim.set_g4_verbose(False)
    sim.set_g4_visualisation_flag(False)
    sim.set_g4_multi_thread(False)
    sim.set_g4_random_engine("MersenneTwister", 12346)

    # set the world size like in the Gate macro
    m = gam.g4_units('m')
    world = sim.get_volume_info('World')
    world.size = [3 * m, 3 * m, 3 * m]

    # add a simple waterbox volume
    waterbox = sim.add_volume('Box', 'Waterbox')
    cm = gam.g4_units('cm')
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = 'G4_WATER'

    # physics
    mm = gam.g4_units('mm')
    p = sim.physics_manager
    # p.name = 'QGSP_BERT_EMZ'
    # p.name = 'G4EmLivermorePhysics'
    p.name = 'G4EmStandardPhysics_option4'
    p.decay = True

    em = p.g4_em_parameters
    em.SetFluo(True)
    em.SetAuger(True)
    em.SetAugerCascade(True)
    em.SetPixe(True)

    cuts = p.production_cuts
    cuts.world.electron = 3 * mm
    cuts.waterbox.gamma = 5 * mm
    p.set_cuts()

    # print info about physics
    print(p)
    print(p.g4_em_parameters.ToString())
    print(p.dump_physics_list())

    # default source for tests
    keV = gam.g4_units('keV')
    Bq = gam.g4_units('Bq')

    source = sim.add_source('Generic')
    source.particle = 'gamma'
    source.energy.mono = 80 * keV
    source.direction.type = 'momentum'
    source.direction.momentum = [0, 0, 1]
    source.activity = 100 * Bq

    source = sim.add_source('Generic')
    source.particle = 'ion 9 18'  # or F18 or Fluorine18
    source.position.type = 'sphere'
    source.position.center = [10 * mm, 10 * mm, 20 * mm]
    source.position.radius = 3 * mm
    source.direction.type = 'iso'
    source.activity = 1000 * Bq

    source = sim.add_source('Generic')
    source.particle = 'ion 53 124'  # 53 124 0 0       # Iodine 124
    source.position.type = 'sphere'
    source.position.center = [-10 * mm, -10 * mm, -40 * mm]
    source.position.radius = 1 * mm
    source.direction.type = 'iso'
    source.activity = 1000 * Bq

    # add stat actor
    sim.add_actor('SimulationStatisticsActor', 'Stats')

    return sim

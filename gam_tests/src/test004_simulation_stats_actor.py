#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = 'MersenneTwister'

# set the world size like in the Gate macro
m = gam.g4_units('m')
world = sim.world
world.size = [3 * m, 3 * m, 3 * m]

# add a simple waterbox volume
waterbox = sim.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'G4_WATER'

# physic list # FIXME will be changed
# print('Phys lists :', sim.get_available_physicLists())

# default source for tests
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')
source = sim.add_source('Generic', 'Default')
source.particle = 'gamma'
source.energy.mono = 80 * keV
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.activity = 200000 * Bq

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# print before init
print(sim)
print('-' * 80)
print(sim.dump_volumes())
print(sim.dump_sources())
print(sim.dump_actors())
print('-' * 80)
print('Volume types :', sim.dump_volume_types())
print('Source types :', sim.dump_source_types())
print('Actor types  :', sim.dump_actor_types())

# create G4 objects
sim.initialize()

# print after init
print(sim)
print('Simulation seed:', sim.actual_random_seed)

# verbose
# sim.g4_apply_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
sim.start()
print(sim.dump_sources())

stats = sim.get_actor('Stats')
print(stats)

# gate_test4_simulation_stats_actor
# Gate mac/main.mac
stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'gate' / 'gate_test004_simulation_stats_actor' / 'output' / 'stat.txt')
print('-' * 80)
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.03)

gam.test_ok(is_ok)

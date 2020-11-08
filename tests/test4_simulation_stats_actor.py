#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import gam_g4 as g4
import time

gam.log.setLevel(gam.DEBUG)
print('MT : ', g4.GamInfo.get_G4MULTITHREADED())

# create the simulation
sim = gam.Simulation()
sim.set_g4_verbose(True)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456)

# set the world size like in the Gate macro
m = gam.g4_units('m')
world = sim.get_volume_info('World')
world.size = [3 * m, 3 * m, 3 * m]

# add a simple volume
waterbox = sim.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'G4_WATER'

# physic list
# print('Phys lists :', sim.get_available_physicLists())

# default source for tests
MeV = gam.g4_units('MeV')
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
source = sim.add_source('TestProtonPy2', 'Default')
source.energy = 80 * keV
source.diameter = 0 * mm
source.n = 200000

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')

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
print('Simulation seed:', sim.seed)

# verbose
#sim.g4_apply_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.RUN)
start_time = time.time()
import time
sim.start()
stop_time = time.time()
sec = gam.g4_units('s')
duration = (stop_time - start_time) * sec
print('duration: ', duration)

stats = sim.get_actor('Stats')
print(stats)

# gate_test4_simulation_stats_actor
# Gate mac/main.mac
stats_ref = gam.read_stat_file('./gate_test4_simulation_stats_actor/output/stat.txt')
print('-' * 80)
gam.assert_stats(stats, stats_ref, tolerance=0.03)

gam.test_ok()

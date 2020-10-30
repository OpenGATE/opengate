#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from scipy.spatial.transform import Rotation

gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(True)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456)
sim.set_g4_random_engine("MersenneTwister") ## auto

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

MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')

# default source for tests
# source = sim.add_source('GenericSource', 'source1')
# source.particle = 'gamma'
# source.energy = 1 * MeV
# source.position = [0, 5, 0]
# source.direction = [0, 0, 1]
# source.activity = 100 * Bq

source = sim.add_source('GenericSource', 'source1')
source.particle = 'proton'
source.energy = 150 * MeV  # source_ene.gauss(mean=100 * MeV, std=5 * MeV)
source.position = gam.get_source_position('G4SPSPosDistribution')
p = source.position.object.generator
p.SetPosDisType('Volume')
p.SetPosDisShape('Sphere')
p.SetCentreCoords(gam.vec_np_as_g4([1 * cm, 2 * cm, 3 * cm]))
p.SetRadius(1 * cm)
source.direction = [0, 0, 1]
source.activity = 4 * Bq

source = sim.add_source('GenericSource', 'source2')
source.particle = 'proton'
source.energy = 150 * MeV  # source_ene.gauss(mean=100 * MeV, std=5 * MeV)
p = source.position = gam.get_source_position('sphere')
p.radius = 1 * cm
p.center = [1 * cm, 2 * cm, 3 * cm]
source.direction = [0, 0, 1]
source.activity = 4 * Bq

#sim.source_manager.sources.pop('source1')
#sim.source_manager.sources.pop('source2')

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
sim.g4_apply_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.EVENT)
sim.start()

stats = sim.get_actor('Stats')
print(stats)

# gate_test10
# Gate mac/main.mac
# stats_ref = gam.read_stat_file('./gate_test4_simulation_stats_actor/output/stat.txt')
# print('-' * 80)
# gam.assert_stats(stats, stats_ref, tolerance=0.03)

# gam.test_ok()

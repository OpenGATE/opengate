#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import platform

gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()
sim.set_g4_verbose(False)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456)

# set the world size like in the Gate macro
m = gam.g4_units('m')
sim.volumes_info.World.size = [3 * m, 3 * m, 3 * m]

# add a simple volume
waterbox = sim.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'G4_WATER'

# physic list
# print('Phys lists :', sim.get_available_physicLists())

# default source for tests
source = sim.add_source('TestProtonPy2', 'Default')
MeV = gam.g4_units('MeV')
source.energy = 150 * MeV
source.diameter = 0 * cm
source.n = 2000

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')

# create G4 objects
sim.initialize()

print(sim.dump_sources())

print('Simulation seed:', sim.seed)
print(sim.dump_volumes())

# verbose
sim.g4_apply_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.RUN)
sim.start()

a = sim.actors_info.Stats.g4_actor
print(a)

# Darwin
track_count = 31281
step_count = 120491
if platform.system() == 'Linux':
    # FIXME BUG ! On linux the results is not always the same (even with the same seed) ???
    track_count = 25359

assert a.run_count == 1
assert a.event_count == 2000
assert a.track_count == track_count
assert a.step_count == step_count
assert a.batch_count == 3

print(f'OSX PPS = ~3856 --> {a.pps:.0f}')

# gate_test4_simulation_stats_actor
# Gate mac/main.mac

# NumberOfRun    = 1
# NumberOfEvents = 2000
# NumberOfTracks = 31499
# NumberOfSteps  = 118655
# NumberOfGeometricalSteps  = 2630
# NumberOfPhysicalSteps     = 116025
# PPS (Primary per sec)     = 4840.43
# TPS (Track per sec)       = 76234.4
# SPS (Step per sec)        = 287171

gam.test_ok()

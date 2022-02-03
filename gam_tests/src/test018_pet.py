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
ui.visu = False
ui.check_volumes_overlap = False

#  change world size
m = gam.g4_units('m')
mm = gam.g4_units('mm')
cm = gam.g4_units('cm')
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]

# add a box (not really useful here)
# prefer air to speed simulation
airbox = sim.add_volume('Box', 'Airbox')
airbox.size = [30 * cm, 30 * cm, 30 * cm]
airbox.translation = [0 * cm, 0 * cm, 0 * cm]
airbox.material = 'G4_AIR'
airbox.color = [0, 0, 1, 1]  # blue

# add a PET ... or two PET !
import contrib.gam_pet as gam_pet

pet1 = gam_pet.add_pet(sim, 'pet1')
# pet2 = gam_vereos.add_pet(sim, 'pet2')
# pet2.translation = [0, 0, pet1.dz * 2]

# default source for tests
source = sim.add_source('Generic', 'Default')
Bq = gam.g4_units('Bq')
source.particle = 'e+'
source.energy.type = 'F18'
source.position.type = 'sphere'
source.position.radius = 5 * cm
source.position.translation = [0, 0, 0]
source.direction.type = 'iso'
source.activity = 1000 * Bq

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'Stats')
s.track_types_flag = True

# create G4 objects
sim.initialize()

# explicit check overlap (already performed during initialize)
# sim.check_volumes_overlap(verbose=True)

# start simulation
sim.start()

# print results
stats = sim.get_actor('Stats')
# stats.write('output_ref/test018_stats_ref.txt')

# check
stats = sim.get_actor('Stats')
stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'output_ref' / 'test018_stats_ref.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.15)

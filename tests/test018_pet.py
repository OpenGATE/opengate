#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import gam_g4 as g4
from scipy.spatial.transform import Rotation
from box import Box, BoxList

# global log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.multi_threading = False
ui.check_volumes_overlap = False
ui.random_seed = 6547897

#  change world size
m = gam.g4_units('m')
mm = gam.g4_units('mm')
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]

# add a waterbox
waterbox = sim.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [30 * cm, 30 * cm, 30 * cm]
waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
waterbox.material = 'G4_WATER'
waterbox.color = [0, 0, 1, 1]  # blue

# add a PET ... no two PET !
import contrib.gam_vereos as gam_vereos

pet1 = gam_vereos.add_pet(sim, 'pet1')
pet2 = gam_vereos.add_pet(sim, 'pet2')
pet2.translation = [0, 0, pet1.Dz * 2]

# default source for tests
source = sim.add_source('Generic', 'Default')
Bq = gam.g4_units('Bq')
source.particle = 'e+'
source.energy.type = 'F18'
source.position.type = 'sphere'
source.position.radius = 5 * cm
source.position.center = [0, 0, 0]
source.direction.type = 'iso'
source.activity = 10000 * Bq

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'Stats')
s.track_types_flag = True

# create G4 objects
sim.initialize()

# explicit check overlap (already performed during initialize)
# sim.check_volumes_overlap(verbose=True)

# start simulation
gam.source_log.setLevel(gam.RUN)
sim.start()

# print results
stats = sim.get_actor('Stats')
print(stats)

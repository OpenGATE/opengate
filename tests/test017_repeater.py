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
ui.check_volumes_overlap = False

#  change world size
m = gam.g4_units('m')
mm = gam.g4_units('mm')
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]

# add a simple volume
airBox = sim.add_volume('Box', 'AirBox')
cm = gam.g4_units('cm')
airBox.size = [30 * cm, 30 * cm, 30 * cm]
airBox.translation = [0 * cm, 0 * cm, 0 * cm]
airBox.material = 'G4_AIR'
airBox.color = [0, 0, 1, 1]  # blue

# lyso material
n = g4.G4NistManager.Instance()
print(n)
elems = ['Lu']  # , 'Yttrium', 'Silicon', 'Oxygen']
nbAtoms = [18]  # , 2, 10, 50]
gcm3 = gam.g4_units('g/cm3')
n.ConstructNewMaterial('LYSO', elems, nbAtoms, 7.1 * gcm3)

# repeat a box
crystal = sim.add_volume('Box', 'crystal')
crystal.mother = 'AirBox'
crystal.size = [1 * cm, 1 * cm, 1 * cm]
crystal.translation = None
crystal.rotation = None
crystal.material = 'LYSO'
m = Rotation.identity().as_matrix()
le = [{'name': 'crystal1', 'translation': [1 * cm, 0 * cm, 0], 'rotation': m},
      {'name': 'crystal2', 'translation': [0.2 * cm, 2 * cm, 0], 'rotation': m},
      {'name': 'crystal3', 'translation': [-0.2 * cm, 4 * cm, 0], 'rotation': m},
      {'name': 'crystal4', 'translation': [0, 6 * cm, 0], 'rotation': m}]
print(crystal)
print(le)
crystal.repeat = le

# default source for tests
source = sim.add_source('Generic', 'Default')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
source.particle = 'gamma'
source.energy.mono = 0.511 * MeV
source.position.type = 'sphere'
source.position.radius = 1 * cm
source.position.translation = [0, 0, 0]
source.direction.type = 'momentum'
source.direction.momentum = [0, 1, 0]
source.activity = 10000 * Bq

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'Stats')
s.track_types_flag = True

# dose actor
d = sim.add_actor('DoseActor', 'dose')
d.save = 'output/test017-edep.mhd'
# d.save = 'output_ref/test017-edep-ref.mhd'
d.mother = 'crystal'
d.dimension = [150, 150, 150]
mm = gam.g4_units('mm')
d.spacing = [1 * mm, 1 * mm, 1 * mm]
d.translation = [5 * mm, 0 * mm, 0 * mm]

# create G4 objects
sim.initialize()

# explicit check overlap (already performed during initialize)
sim.check_volumes_overlap(verbose=True)

# start simulation
gam.source_log.setLevel(gam.RUN)
sim.start()

# print results
stats = sim.get_actor('Stats')
# stats.write('output_ref/test017-stats-ref.txt')

# tests
stats_ref = gam.read_stat_file('./output_ref/test017-stats-ref.txt')
is_ok = gam.assert_stats(stats, stats_ref, 0.08)
is_ok = is_ok and gam.assert_images('output/test017-edep.mhd', 'output_ref/test017-edep-ref.mhd',
                                    stats, tolerance=0.2)

gam.test_ok(is_ok)

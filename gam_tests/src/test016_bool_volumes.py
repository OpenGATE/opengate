#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
from scipy.spatial.transform import Rotation
import pathlib

pathFile = pathlib.Path(__file__).parent.resolve()

# global log level
# create the simulation
sim = gam.Simulation()
print(f'Volumes types: {sim.dump_volume_types()}')

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False

# add a material database
sim.add_material_database(pathFile / '..' / 'data' / 'GateMaterials.db')

#  change world size
m = gam.g4_units('m')
cm = gam.g4_units('cm')
mm = gam.g4_units('mm')
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# create a union of several volumes

# first create the solids
b = sim.new_solid('Box', 'box')
b.size = [10 * cm, 10 * cm, 10 * cm]
s = sim.new_solid('Sphere', 'sphere')
s.rmax = 5 * cm
t = sim.new_solid('Tubs', 't')
t.rmin = 0
t.rmax = 2 * cm
t.dz = 15 * cm

# bool operations
a = gam.solid_union(b, s, [0, 1 * cm, 5 * cm])
a = gam.solid_subtraction(a, t, [0, 1 * cm, 5 * cm])
a = gam.solid_union(a, b, [0, -1 * cm, -5 * cm])  # strange but ok
b = gam.solid_intersection(t, s, [3 * cm, 0, 0])
a = gam.solid_union(a, b, [0, -7 * cm, -5 * cm])

# then add them to a Union, with translation/rotation
rot = Rotation.from_euler('x', 33, degrees=True).as_matrix()
u = sim.add_volume_from_solid(a, 'my_stuff')
u.translation = [5 * cm, 5 * cm, 5 * cm]
u.rotation = rot
u.mother = 'world'
u.material = 'G4_WATER'
u.color = [0, 1, 0, 1]

# create a volume from a solid (not really useful)
u = sim.add_volume_from_solid(s, 'test_sph')
u.translation = [-5 * cm, -5 * cm, 1 - 5 * cm]
u.mother = 'world'
u.material = 'G4_WATER'
u.color = [0, 1, 1, 1]

# default source for tests
source = sim.add_source('Generic', 'Default')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
source.particle = 'proton'
source.energy.mono = 240 * MeV
source.position.radius = 1 * cm
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.activity = 5 * Bq

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# create G4 objects
print(sim)
sim.initialize()

# explicit check overlap (already performed during initialize)
sim.check_volumes_overlap(verbose=True)

# start simulation
sim.start()

# print results at the end
stats = sim.get_actor('Stats')
print(stats)

# check
# FIXME

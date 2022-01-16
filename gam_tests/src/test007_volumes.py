#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
from scipy.spatial.transform import Rotation
import pathlib
import os

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
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]

# add a simple volume
waterbox = sim.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [60 * cm, 60 * cm, 60 * cm]
waterbox.translation = [0 * cm, 0 * cm, 35 * cm]
waterbox.material = 'G4_WATER'
waterbox.color = [0, 0, 1, 1]  # blue

# another (child) volume with rotation
mm = gam.g4_units('mm')
sheet = sim.add_volume('Box', 'Sheet')
sheet.size = [30 * cm, 30 * cm, 2 * mm]
sheet.mother = 'Waterbox'
sheet.material = 'Lead'
r = Rotation.from_euler('x', 33, degrees=True)
center = [0 * cm, 0 * cm, 10 * cm]
t = gam.get_translation_from_rotation_with_center(r, center)
sheet.rotation = r.as_matrix()
sheet.translation = t + [0 * cm, 0 * cm, -18 * cm]
sheet.color = [1, 0, 0, 1]  # red

# A sphere
sph = sim.add_volume('Sphere', 'mysphere')
sph.rmax = 5 * cm
sph.mother = 'Waterbox'
sph.translation = [0 * cm, 0 * cm, -8 * cm]
sph.material = 'Lung'
sph.color = [0.5, 1, 0.5, 1]  # kind of green
sph.toto = 'nothing'  # ignored, should raise a warning

# A ...thing ?
trap = sim.add_volume('Trap', 'mytrap')
trap.mother = 'Waterbox'
trap.translation = [0, 0, 15 * cm]
trap.material = 'G4_LUCITE'

# default source for tests
source = sim.add_source('Generic', 'Default')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
source.particle = 'proton'
source.energy.mono = 240 * MeV
source.position.radius = 1 * cm
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.activity = 2500 * Bq

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# run timing 
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 0.5 * sec]
                            # ,[0.5 * sec, 1.2 * sec]
                            ]

# create G4 objects
print(sim)
sim.initialize()

# explicit check overlap (already performed during initialize)
sim.check_volumes_overlap(verbose=True)

# print info material db
dbn = sim.dump_material_database_names()
mnist = sim.dump_material_database('NIST')
mdb = sim.dump_material_database(pathFile / '..' / 'data' / 'GateMaterials.db')
dm = sim.dump_defined_material()
print('Material info:')
print('\t databases    :', dbn)
print('\t mat in NIST  :', len(mnist), mnist)
print('\t mat in db    :', mdb)
print('\t defined mat  :', dm)

assert dbn == [pathFile / '..' / 'data' / 'GateMaterials.db', 'NIST']
assert len(mnist) == 308
assert mdb == ['Vacuum', 'Aluminium', 'Uranium', 'Silicon', 'Germanium', 'Yttrium', 'Gadolinium', 'Lutetium',
               'Tungsten', 'Lead', 'Bismuth', 'NaI', 'NaITl', 'PWO', 'BGO', 'LSO', 'Plexiglass', 'GSO', 'LuAP', 'YAP',
               'Water',
               'Quartz', 'Breast', 'Air', 'Glass', 'Scinti-C9H10', 'LuYAP-70', 'LuYAP-80', 'Plastic', 'CZT', 'Lung',
               'Polyethylene', 'PVC', 'SS304', 'PTFE', 'LYSO', 'Body', 'Muscle', 'LungMoby', 'SpineBone', 'RibBone',
               'Adipose', 'Blood', 'Heart', 'Kidney', 'Liver', 'Lymph', 'Pancreas', 'Intestine', 'Skull', 'Cartilage',
               'Brain', 'Spleen', 'Testis', 'PMMA']
assert dm == ['G4_AIR', 'G4_WATER', 'Lead', 'Lung', 'G4_LUCITE']

# verbose
sim.apply_g4_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
sim.start()

# print results at the end
stats = sim.get_actor('Stats')
print(stats)

# check
assert len(sim.dump_defined_material()) == 5
stats_ref = gam.SimulationStatisticsActor()
c = stats_ref.counts
c.run_count = 1
c.event_count = 1280
c.track_count = 17034  # 25668
c.step_count = 78096  # 99465
# stats_ref.pps = 506.6
sec = gam.g4_units('second')
c.duration = 2.5267 * sec
print('-' * 80)
is_ok = gam.assert_stats(stats, stats_ref, 0.15)

gam.test_ok(is_ok)

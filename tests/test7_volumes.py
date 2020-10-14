#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from scipy.spatial.transform import Rotation

# global log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()

# verbose and GUI
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(True)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456)

# add a material database
sim.add_material_database('GateMaterials.db')

#  change world size
m = gam.g4_units('m')
sim.volumes_info.World.size = [1.5 * m, 1.5 * m, 1.5 * m]

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
sph.Rmax = 5 * cm
# sph.toto = 12  # ignored
sph.mother = 'Waterbox'
sph.translation = [0 * cm, 0 * cm, -8 * cm]
sph.material = 'Lung'
sph.color = [0.5, 1, 0.5, 1]  # kind of green

# A ...thing ?
trap = sim.add_volume('Trap', 'mytrap')
trap.mother = 'Waterbox'
trap.translation = [0, 0, 15 * cm]
trap.material = 'G4_LUCITE'

# default source for tests
source = sim.add_source('TestProtonTime', 'Default')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
source.energy = 240 * MeV
source.radius = 1 * cm
source.activity = 50 * Bq

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')

# run timing 
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 0.5 * sec]
                            # ,[0.5 * sec, 1.2 * sec]
                            ]

print(f'Source types: {sim.dump_source_types()}')
print(sim.dump_sources())
print(sim.dump_volumes())

# create G4 objects
sim.initialize()

# explicit check overlap (already performed during initialize)
sim.check_geometry_overlaps(verbose=True)

# print info
print(sim.dump_volumes())

# print info material db
dbn = sim.dump_material_database_names()
mnist = sim.dump_material_database('NIST')
mdb = sim.dump_material_database('GateMaterials.db')
dm = sim.dump_defined_material()
print('Material info:')
print('\t databases    :', dbn)
print('\t mat in NIST  :', len(mnist), mnist)
print('\t mat in db    :', mdb)
print('\t defined mat  :', dm)

assert dbn == ['GateMaterials.db', 'NIST']
assert len(mnist) == 308
assert mdb == ['Vacuum', 'Aluminium', 'Uranium', 'Silicon', 'Germanium', 'Yttrium', 'Gadolinium', 'Lutetium', 'Tungsten', 'Lead', 'Bismuth', 'NaI', 'PWO', 'BGO', 'LSO', 'Plexiglass', 'GSO', 'LuAP', 'YAP', 'Water', 'Quartz', 'Breast', 'Air', 'Glass', 'Scinti-C9H10', 'LuYAP-70', 'LuYAP-80', 'Plastic', 'CZT', 'Lung', 'Polyethylene', 'PVC', 'SS304', 'PTFE', 'LYSO', 'Body', 'Muscle', 'LungMoby', 'SpineBone', 'RibBone', 'Adipose', 'Blood', 'Heart', 'Kidney', 'Liver', 'Lymph', 'Pancreas', 'Intestine', 'Skull', 'Cartilage', 'Brain', 'Spleen', 'Testis', 'PMMA']
assert dm == ['G4_AIR', 'G4_WATER', 'Lead', 'Lung', 'G4_LUCITE']

# verbose
sim.g4_apply_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.RUN)
sim.start()

# print results at the end
stat = sim.actors_info.Stats.g4_actor
print(stat)

# check
assert len(sim.dump_defined_material()) == 5
assert stat.run_count == 1
assert stat.event_count == 26
assert stat.track_count == 534
assert stat.step_count == 2088

gam.test_ok()

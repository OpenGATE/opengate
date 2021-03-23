#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from scipy.spatial.transform import Rotation

# global log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()
print(f'Volumes types: {sim.dump_volume_types()}')

# verbose and GUI
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(False)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456)

# add a material database
sim.add_material_database('./data/GateMaterials.db')

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
sph.Rmax = 5 * cm
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
source = sim.add_source('Generic', 'Default')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
source.particle = 'proton'
source.energy.mono = 240 * MeV
source.position.radius = 1 * cm
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.activity = 500 * Bq


source = sim.add_source('Generic', 'source1')
source.particle = 'gamma'
source.activity = 10000 * Bq
source.position.type = 'sphere'
source.position.radius = 5 * mm
source.position.center = [-3 * cm, 30 * cm, -3 * cm]
source.direction.type = 'momentum'
source.direction.momentum = [0, -1, 0]
source.energy.type = 'mono'
source.energy.mono = 1 * MeV

source = sim.add_source('Generic', 'source2')
source.particle = 'proton'
source.activity = 10000 * Bq
source.position.type = 'disc'
source.position.radius = 5 * mm
source.position.center = [6 * cm, 5 * cm, -30 * cm]
# source.position.rotation = Rotation.from_euler('x', 45, degrees=True).as_matrix()
source.position.rotation = Rotation.identity().as_matrix()
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.energy.type = 'gauss'
source.energy.mono = 140 * MeV
source.energy.sigma_gauss = 10 * MeV

source = sim.add_source('Generic', 's3')
source.particle = 'proton'
source.activity = 10000 * Bq
source.position.type = 'box'
source.position.size = [4 * cm, 4 * cm, 4 * cm]
source.position.center = [8 * cm, 8 * cm, 30 * cm]
source.direction.type = 'focused'
source.direction.focus_point = [1 * cm, 2 * cm, 3 * cm]
source.energy.type = 'gauss'
source.energy.mono = 140 * MeV
source.energy.sigma_gauss = 10 * MeV

source = sim.add_source('Generic', 's4')
source.particle = 'proton'
source.activity = 10000 * Bq
source.position.type = 'box'
source.position.size = [4 * cm, 4 * cm, 4 * cm]
source.position.center = [-3 * cm, -3 * cm, -3 * cm]
# source.position.rotation = Rotation.from_euler('x', 45, degrees=True).as_matrix()
source.position.rotation = Rotation.identity().as_matrix()
source.direction.type = 'iso'
source.energy.type = 'gauss'
source.energy.mono = 80 * MeV
source.energy.sigma_gauss = 1 * MeV


# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# run timing 
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 0.5 * sec]
                            # ,[0.5 * sec, 1.2 * sec]
                            ]


# --------------- settings

"""

WORK IN PROGRESS not finished

"""

ui = sim.get_user_info()
print('All ui', ui)
print()
print('vol', sim.volume_manager.volumes)
exit(0)


# create G4 objects
print(sim)
sim.initialize()

# explicit check overlap (already performed during initialize)
sim.check_geometry_overlaps(verbose=True)

# verbose
#sim.apply_g4_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.RUN)
sim.start()

# print results at the end
stats = sim.get_actor('Stats')
print(stats)

# check
assert len(sim.dump_defined_material()) == 5
stats_ref = gam.SimulationStatisticsActor('test')
stats_ref.SetRunCount(1)
stats_ref.SetEventCount(234)
stats_ref.SetTrackCount(4544)
stats_ref.SetStepCount(17485)
# stats_ref.pps = 2150
sec = gam.g4_units('second')
stats_ref.fDuration = 0.01116279069 * sec
print('-' * 80)
is_ok = gam.assert_stats(stats, stats_ref, 0.05)

gam.test_ok(is_ok)

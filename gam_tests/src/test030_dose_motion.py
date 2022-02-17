#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
from scipy.spatial.transform import Rotation

paths = gam.get_common_test_paths(__file__, 'gate_test029_volume_time_rotation')

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False

# units
m = gam.g4_units('m')
mm = gam.g4_units('mm')
cm = gam.g4_units('cm')
um = gam.g4_units('um')
nm = gam.g4_units('nm')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
sec = gam.g4_units('second')

#  change world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# add a simple fake volume to test hierarchy
# translation and rotation like in the Gate macro
fake = sim.add_volume('Box', 'fake')
fake.size = [40 * cm, 40 * cm, 40 * cm]
fake.translation = [1 * cm, 2 * cm, 3 * cm]
fake.material = 'G4_AIR'
fake.color = [1, 0, 1, 1]

# waterbox
waterbox = sim.add_volume('Box', 'waterbox')
waterbox.mother = 'fake'
waterbox.size = [20 * cm, 20 * cm, 20 * cm]
waterbox.translation = [-3 * cm, -2 * cm, -1 * cm]
waterbox.rotation = Rotation.from_euler('y', -20, degrees=True).as_matrix()
waterbox.material = 'G4_WATER'
waterbox.color = [0, 0, 1, 1]

# physics
sim.set_cut('world', 'all', 700 * um)

# default source for tests
# the source is fixed at the center, only the volume will move
source = sim.add_source('Generic', 'mysource')
source.energy.mono = 150 * MeV
source.particle = 'proton'
source.position.type = 'disc'
source.position.radius = 5 * mm
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.activity = 20000 * Bq

# add dose actor
dose = sim.add_actor('DoseActor', 'dose')
dose.save = paths.output / 'test030-edep.mhd'
dose.mother = 'waterbox'
dose.dimension = [99, 99, 99]
mm = gam.g4_units('mm')
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.translation = [2 * mm, 3 * mm, -2 * mm]
dose.uncertainty = True

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'Stats')
s.track_types_flag = True
s.output = paths.output / 'stats030.txt'

# motion
motion = sim.add_actor('MotionVolumeActor', 'Orbiting')
motion.mother = fake.name
motion.translations = []
motion.rotations = []
sim.run_timing_intervals = []
n = 3
start = 0
gantry_rotation = start
end = 1 * sec / n
for r in range(n):
    t, rot = gam.get_transform_orbiting(fake.translation, 'Y', gantry_rotation)
    rot = gam.rot_np_as_g4(rot)
    motion.translations.append(t)
    motion.rotations.append(rot)
    sim.run_timing_intervals.append([start, end])
    gantry_rotation += 20
    start = end
    end += 1 * sec / n

# create G4 objects
sim.initialize()

# Check

# start simulation
sim.start()

# print results at the end
stat = sim.get_actor('Stats')
print(stat)

dose = sim.get_actor('dose')
print(dose)

# tests
stats_ref = gam.read_stat_file(paths.output_ref / 'stats030.txt')
is_ok = gam.assert_stats(stat, stats_ref, 0.10)

print()
gam.warning('Difference for EDEP')
is_ok = gam.assert_images(paths.output / 'test030-edep.mhd',
                          paths.output_ref / 'test030-edep.mhd',
                          stat, tolerance=30, ignore_value=0) and is_ok

print('\nDifference for uncertainty')
is_ok = gam.assert_images(paths.output / 'test030-edep_uncertainty.mhd',
                          paths.output_ref / 'test030-edep_uncertainty.mhd',
                          stat, tolerance=10, ignore_value=1) and is_ok

gam.test_ok(is_ok)

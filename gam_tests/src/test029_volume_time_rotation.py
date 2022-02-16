#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_ge_nm670_spect as gam_spect
import contrib.gam_iec_phantom as gam_iec
from scipy.spatial.transform import Rotation

paths = gam.get_common_test_paths(__file__, 'gate_test029_volume_time_rotation')

# create the main simulation object
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = 1

# some basic units
m = gam.g4_units('m')
cm = gam.g4_units('cm')
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')
deg = gam.g4_units('deg')
sec = gam.g4_units('second')
kBq = 1000 * Bq

# world size
world = sim.world
world.size = [2 * m, 2 * m, 2 * m]
world.material = 'G4_AIR'

# spect head
spect = gam_spect.add_spect(sim, 'spect', collimator=False, debug=False)
initial_rot = Rotation.from_euler('X', 90, degrees=True)
t, rot = gam.get_transform_orbiting([0, 25 * cm, 0], 'Z', 0)
rot = Rotation.from_matrix(rot)
spect.translation = t
spect.rotation = (rot * initial_rot).as_matrix()

# iec phantom
iec_phantom = gam_iec.add_phantom(sim)

# two sources (no background yet)
activity_concentration = 5 * kBq / ui.number_of_threads
ac = activity_concentration
sources = gam_iec.add_spheres_sources(sim, 'iec', 'iec_source',
                                      [10, 13, 17, 22, 28, 37],
                                      [ac, ac, ac, ac, ac, ac])
for s in sources:
    s.particle = 'gamma'
    s.energy.type = 'mono'
    s.energy.mono = 140 * keV
    s.direction.type = 'iso'
    s.direction.type = 'momentum'
    s.direction.momentum = [0, 1, 0]
    s.direction.angle_acceptance_volume = 'spect'

sources = gam_iec.add_spheres_sources(sim, 'iec', 'iec_source2',
                                      [10, 13, 17, 22, 28, 37],
                                      [ac, ac, ac, ac, ac, ac])
for s in sources:
    s.particle = 'gamma'
    s.energy.type = 'mono'
    s.energy.mono = 140 * keV
    s.direction.type = 'iso'
    s.direction.type = 'momentum'
    s.direction.momentum = [1, 0, 0]
    s.direction.angle_acceptance_volume = 'spect'

# physic list
sim.set_physics_list('G4EmStandardPhysics_option4')
sim.set_cut('world', 'all', 10 * mm)
sim.set_cut('spect', 'all', 1 * mm)

# add stat actor
stat = sim.add_actor('SimulationStatisticsActor', 'Stats')
stat.output = paths.output / 'stats029.txt'

# hits collection
hc = sim.add_actor('HitsCollectionActor', 'Hits')
hc.mother = 'spect_crystal'
hc.output = ''  # No output
hc.attributes = ['PostPosition', 'TotalEnergyDeposit']

# singles collection
sc = sim.add_actor('HitsAdderActor', 'Singles')
sc.mother = hc.mother
sc.input_hits_collection = 'Hits'
sc.policy = 'TakeEnergyCentroid'
sc.output = hc.output

# EnergyWindows
cc = sim.add_actor('HitsEnergyWindowsActor', 'EnergyWindows')
cc.mother = hc.mother
cc.input_hits_collection = 'Singles'
cc.channels = [{'name': 'scatter', 'min': 114 * keV, 'max': 126 * keV},
               {'name': 'peak140', 'min': 126 * keV, 'max': 154.55 * keV}
               ]
cc.output = hc.output

# projection
# (FIXME: visu does not work on Linux when python callback during run)
proj = sim.add_actor('HitsProjectionActor', 'Projection')
proj.mother = hc.mother
proj.input_hits_collections = ['Singles', 'scatter', 'peak140']
proj.spacing = [4.41806 * mm, 4.41806 * mm]
proj.dimension = [128, 128]
proj.output = paths.output / 'proj029.mhd'

# motion of the spect, create also the run time interval
motion = sim.add_actor('MotionVolumeActor', 'Move')
motion.mother = spect.name
motion.translations = []
motion.rotations = []
n = 9
sim.run_timing_intervals = []
start = -90
gantry_rotation = start
end = 1 * sec / n
initial_rot = Rotation.from_euler('X', 90, degrees=True)
for r in range(n):
    t, rot = gam.get_transform_orbiting([0, 30 * cm, 0], 'Z', gantry_rotation)
    rot = Rotation.from_matrix(rot)
    rot = rot * initial_rot
    rot = gam.rot_np_as_g4(rot.as_matrix())
    motion.translations.append(t)
    motion.rotations.append(rot)
    sim.run_timing_intervals.append([start, end])
    gantry_rotation += 10
    start = end
    end += 1 * sec / n

print(f'Run intervals: {sim.run_timing_intervals}')

# check actor priority: the MotionVolumeActor must be first
l = [l for l in sim.actor_manager.user_info_actors.values()]
sorted_actors = sorted(l, key=lambda d: d.priority)
print(f'Actors order: ', [[l.name, l.priority] for l in sorted_actors])

# initialize & start
sim.initialize()
sim.start()

# WARNING when "angle_acceptance_volume" is enabled, it is a bit faster (+50%)
# but the result is not exactly the same as without. This is because, even
# if the initial particle is not in the direction of the spect system,
# it can scatter and still reach the detector.
# We don't have the collimator here (to faster the simulation), this is why the
# difference is not negligible.
# (the reference has been made without the "angle_acceptance_volume" option).

# -------------------------
gam.warning('Compare stats')
stats = gam.read_stat_file(paths.output / 'stats029.txt')
print(stats)
stats_ref = gam.read_stat_file(paths.output_ref / 'stats029.txt')
print(f'Number of steps was {stats.counts.step_count}, force to the same value (because of angle acceptance). ')
stats.counts.step_count = stats_ref.counts.step_count  # force to id
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.01)
print(is_ok)

gam.warning('Compare images')
# read image and force change the offset to be similar to old Gate
is_ok = gam.assert_images(paths.output / 'proj029.mhd',
                          paths.output_ref / 'proj029.mhd',
                          stats, tolerance=50, ignore_value=0, axis='x') and is_ok
print(is_ok)

gam.test_ok(is_ok)

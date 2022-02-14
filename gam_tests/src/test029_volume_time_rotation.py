#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import gam_g4 as g4
import contrib.gam_ge_nm670_spect as gam_spect
import contrib.gam_iec_phantom as gam_iec
from scipy.spatial.transform import Rotation

paths = gam.get_common_test_paths(__file__, 'gate_test029_volume_time_rotation')

sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = 1
ui.random_seed = 123456

# units
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
spect.translation = t
spect.rotation = (rot * initial_rot).as_matrix()

# iec phantom
iec_phantom = gam_iec.add_phantom(sim)

# sources (no background yet)
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
    # s.direction.angle_acceptance_volume = 'spect'

# physic list
sim.set_physics_list('G4EmStandardPhysics_option4')
sim.set_cut('world', 'all', 10 * mm)
sim.set_cut('spect', 'all', 0.1 * mm)

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# motion of the spect
motion = sim.add_actor('MotionVolumeActor', 'Orbiting')
motion.mother = spect.name
motion.translations = []
motion.rotations = []
n = 10
sim.run_timing_intervals = []
start = 0
gantry_rotation = start
end = 1 * sec / n
initial_rot = Rotation.from_euler('X', 90, degrees=True)
for r in range(n):
    t, rot = gam.get_transform_orbiting([0, 30 * cm, 0], 'Z', gantry_rotation)
    rot = rot * initial_rot
    rot = gam.rot_np_as_g4(rot.as_matrix())
    # transform = g4.G4Transform3D(rot, t)
    motion.translations.append(t)
    motion.rotations.append(rot)
    print(t, rot)
    sim.run_timing_intervals.append([start, end])
    gantry_rotation += 20
    print(gantry_rotation)
    start = end
    end += 1 * sec / n
print(motion)
print(sim.run_timing_intervals)

# hits collection
hc = sim.add_actor('HitsCollectionActor', 'Hits')
# get crystal volume by looking for the word crystal in the name
l = sim.get_all_volumes_user_info()
crystal = l[[k for k in l if 'crystal' in k][0]]
print(crystal.name)
hc.mother = crystal.name
hc.output = ''  # No output paths.output / 'test028.root'
hc.attributes = ['PostPosition', 'TotalEnergyDeposit']

# singles collection
sc = sim.add_actor('HitsAdderActor', 'Singles')
sc.mother = crystal.name
sc.input_hits_collection = 'Hits'
sc.policy = 'TakeEnergyWinner'
# sc.policy = 'TakeEnergyCentroid'
sc.output = hc.output

# EnergyWindows
cc = sim.add_actor('HitsEnergyWindowsActor', 'EnergyWindows')
cc.mother = crystal.name
cc.input_hits_collection = 'Singles'
cc.channels = [{'name': 'scatter', 'min': 114 * keV, 'max': 126 * keV},
               {'name': 'peak140', 'min': 126 * keV, 'max': 154.55 * keV}
               ]
cc.output = hc.output

# run timing
# sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1 * sec]]


# projection
# FIXME warning visu does not work when python callback during run
l = sim.get_all_volumes_user_info()
crystal = l[[k for k in l if 'crystal' in k][0]]
# 2D binning projection
proj = sim.add_actor('HitsProjectionActor', 'Projection')
proj.mother = crystal.name
# we set two times the spectrum channel to compare with Gate output
proj.input_hits_collections = ['Singles', 'scatter', 'peak140', 'Singles']
proj.input_hits_collections = ['peak140']
proj.spacing = [4.41806 * mm, 4.41806 * mm]
proj.dimension = [128, 128]
# proj.plane = 'XY' # not implemented yet
proj.output = paths.output / 'proj029.mhd'


# initialize & start
sim.initialize()
sim.start()

# -------------------------
stats = sim.get_actor('Stats')
print(stats)

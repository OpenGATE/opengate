#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import platform
from scipy.spatial.transform import Rotation

# global log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()

# verbose and GUI
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(False) ## VERY slow for the moment. To change for slices

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456)

# add a material database
sim.add_material_database('data/GateMaterials.db')

#  change world size
m = gam.g4_units('m')
world = sim.get_volume_info('world')
world.size = [1 * m, 1 * m, 1 * m]

# add a simple fake volume to test hierarchy
# translation and rotation like in the Gate macro
fake = sim.add_volume('Box', 'fake')
cm = gam.g4_units('cm')
fake.size = [40 * cm, 40 * cm, 40 * cm]
fake.material = 'G4_AIR'
fake.color = [1, 0, 1, 1]
fake.rotation = Rotation.from_euler('x', 20, degrees=True).as_matrix()

# image
patient = sim.add_volume('Image', 'patient')
patient.image = 'data/patient-4mm.mhd'
patient.mother = 'fake'
patient.material = 'G4_AIR'  # material used by default
patient.voxel_materials = [[-900, 'G4_AIR'],
                           [-100, 'Lung'],
                           [0, 'G4_ADIPOSE_TISSUE_ICRP'],
                           [300, 'G4_TISSUE_SOFT_ICRP'],
                           [800, 'G4_B-100_BONE'],
                           [6000, 'G4_BONE_COMPACT_ICRU']]
# or alternatively, from a file (like in Gate)
vm = gam.read_voxel_materials('./gate_test9_voxels/data/patient-HU2mat-v1.txt')
assert vm == patient.voxel_materials
patient.voxel_materials = vm
# write the image of labels (None by default)
patient.dump_label_image = './output/label.mhd'

# default source for tests
source = sim.add_source('Generic', 'mysource')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
mm = gam.g4_units('mm')
source.energy.mono = 130 * MeV
source.particle = 'proton'
source.position.radius = 10 * mm
source.position.center = [0, 0, -14 * cm]
source.activity = 3000 * Bq
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]

# add dose actor
dose = sim.add_actor('DoseActor', 'dose')
dose.save = 'output/test9-edep.mhd'
dose.attached_to = 'patient'
dose.dimension = [99, 99, 99]
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.img_coord_system = True  # default is True
dose.translation = [2 * mm, 3 * mm, -2 * mm]

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# create G4 objects
sim.initialize()

# print info
print(sim.dump_volumes())

# verbose
sim.apply_g4_command('/tracking/verbose 0')

# start simulation
gam.source_log.setLevel(gam.RUN)
sim.start()

# print results at the end
stat = sim.get_actor('Stats')
print(stat)
d = sim.get_actor('dose')
print(d)

# tests
stats_ref = gam.read_stat_file('./gate_test9_voxels/output/stat.txt')
is_ok = gam.assert_stats(stat, stats_ref, 0.1)
is_ok = gam.assert_images('output/test9-edep.mhd', 'gate_test9_voxels/output/output-Edep.mhd', tolerance=0.07)

gam.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import platform
from scipy.spatial.transform import Rotation
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# global log level
# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False

# add a material database
sim.add_material_database(pathFile / '..' / 'data' / 'GateMaterials.db')

# units
m = gam.g4_units('m')
cm = gam.g4_units('cm')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
mm = gam.g4_units('mm')

#  change world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# add a simple fake volume to test hierarchy
# translation and rotation like in the Gate macro
fake = sim.add_volume('Box', 'fake')
fake.size = [40 * cm, 40 * cm, 40 * cm]
fake.material = 'G4_AIR'
fake.color = [1, 0, 1, 1]
fake.rotation = Rotation.from_euler('x', 20, degrees=True).as_matrix()

# image
patient = sim.add_volume('Image', 'patient')
patient.image = pathFile / '..' / 'data' / 'patient-4mm.mhd'
patient.mother = 'fake'
patient.material = 'G4_AIR'  # material used by default
patient.voxel_materials = [[-900, 'G4_AIR'],
                           [-100, 'Lung'],
                           [0, 'G4_ADIPOSE_TISSUE_ICRP'],
                           [300, 'G4_TISSUE_SOFT_ICRP'],
                           [800, 'G4_B-100_BONE'],
                           [6000, 'G4_BONE_COMPACT_ICRU']]
# or alternatively, from a file (like in Gate)
vm = gam.read_voxel_materials(pathFile / '..' / 'data' / 'gate' / 'gate_test009_voxels' / 'data' / 'patient-HU2mat-v1.txt')
assert vm == patient.voxel_materials
patient.voxel_materials = vm
# write the image of labels (None by default)
patient.dump_label_image = pathFile / '..' / 'output' / 'test009_label.mhd'

# default source for tests
source = sim.add_source('Generic', 'mysource')
source.energy.mono = 130 * MeV
source.particle = 'proton'
source.position.type = 'sphere'
source.position.radius = 10 * mm
source.position.translation = [0, 0, -14 * cm]
source.activity = 10000 * Bq
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]

# cuts
c = sim.get_physics_user_info().production_cuts
c.patient.electron = 3 * mm

# add dose actor
dose = sim.add_actor('DoseActor', 'dose')
dose.save = pathFile / '..' / 'output' / 'test009-edep.mhd'
dose.mother = 'patient'
dose.dimension = [99, 99, 99]
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.img_coord_system = True  # default is True
dose.translation = [2 * mm, 3 * mm, -2 * mm]

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')
stats.track_types_flag = True

# create G4 objects
sim.initialize()

# print info
print(sim.dump_volumes())

# verbose
sim.apply_g4_command('/tracking/verbose 0')

# start simulation

sim.start()

# print results at the end
stat = sim.get_actor('Stats')
print(stat)
d = sim.get_actor('dose')
print(d)

# tests
stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'gate' / 'gate_test009_voxels' / 'output' / 'stat.txt')
is_ok = gam.assert_stats(stat, stats_ref, 0.15)
is_ok = is_ok and gam.assert_images(pathFile / '..' / 'output' / 'test009-edep.mhd',
                                    pathFile / '..' / 'data' / 'gate' / 'gate_test009_voxels' / 'output' / 'output-Edep.mhd',
                                    stat, tolerance=35)

gam.test_ok(is_ok)

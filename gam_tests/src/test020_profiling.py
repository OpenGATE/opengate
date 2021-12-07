#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
from scipy.spatial.transform import Rotation
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.number_of_threads = 1
print(ui)

# add a material database
sim.add_material_database(pathFile / '..' / 'data' / 'GateMaterials.db')

#  change world size
m = gam.g4_units('m')
mm = gam.g4_units('mm')
um = gam.g4_units('um')
keV = gam.g4_units('keV')
Bq = gam.g4_units('Bq')
kBq = 1000 * Bq
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# add a simple fake volume to test hierarchy
# translation and rotation like in the Gate macro
fake = sim.add_volume('Box', 'fake')
cm = gam.g4_units('cm')
fake.size = [40 * cm, 40 * cm, 40 * cm]
fake.material = 'G4_WATER'
fake.color = [1, 0, 1, 1]
fake.rotation = Rotation.from_euler('x', 2, degrees=True).as_matrix()

# image
patient = sim.add_volume('Image', 'patient')
patient.image = pathFile / '..' / 'data' / 'patient-4mm.mhd'
patient.mother = 'fake'
patient.material = 'G4_AIR'  # default material
vm = gam.read_voxel_materials(pathFile / '..' / 'data' / 'gate' / 'gate_test009_voxels' / 'data' / 'patient-HU2mat-v1.txt')
patient.voxel_materials = vm
patient.dump_label_image = pathFile / '..' / 'output' / 'test020_labels.mhd'

# activity
activity = 100 * kBq

# source 1
source = sim.add_source('Generic', 'source1')
source.energy.mono = 150 * keV
source.particle = 'gamma'
source.position.type = 'sphere'
source.position.radius = 10 * mm
source.position.translation = [0, 0, -15 * cm]
source.activity = activity / ui.number_of_threads
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]

# large cuts, no e- needed
p = sim.get_physics_user_info()
p.physics_list_name = 'QGSP_BERT_EMV'
c = p.production_cuts
c.world.gamma = 700 * um
c.world.positron = 1 * mm
c.world.electron = 1 * m
c.world.proton = 1 * m

# add dose actor
dose = sim.add_actor('DoseActor', 'dose')
dose.save = pathFile / '..' / 'output' / 'test20-edep.mhd'
dose.mother = 'patient'
# dose.attached_to = 'fake'
dose.dimension = [63, 63, 55]
dose.dimension = [100, 100, 100]
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.img_coord_system = True  # default is True
dose.translation = [0 * mm, 0 * mm, 1 * mm]

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')
stats.track_types_flag = True

# create G4 objects
sim.initialize()

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
stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'gate' / 'gate_test009_voxels' / 'output' / 'stat_profiling.txt')
stats_ref.counts.run_count = ui.number_of_threads
is_ok = gam.assert_stats(stat, stats_ref, 0.1)
is_ok = is_ok and gam.assert_images(pathFile / '..' / 'output' / 'test20-edep.mhd',
                                    pathFile / '..' / 'data' / 'gate' / 'gate_test009_voxels' / 'output' / 'output_profiling-Edep.mhd',
                                    stat, tolerance=78)
gam.test_ok(is_ok)

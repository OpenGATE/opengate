#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import itk
from scipy.spatial.transform import Rotation
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = 1
print(ui)

# add a material database
sim.add_material_database(pathFile / '..' / 'data' / 'GateMaterials.db')

# units
m = gam.g4_units('m')
mm = gam.g4_units('mm')
cm = gam.g4_units('cm')
keV = gam.g4_units('keV')
Bq = gam.g4_units('Bq')
kBq = 1000 * Bq

#  change world size
world = sim.world
world.size = [1.5 * m, 1 * m, 1 * m]

# fake box
b = sim.add_volume('Box', 'fake1')
b.size = [36 * cm, 36 * cm, 36 * cm]
b.translation = [25 * cm, 0, 0]
r = Rotation.from_euler('y', -25, degrees=True)
r = r * Rotation.from_euler('x', -35, degrees=True)
b.rotation = r.as_matrix()
b = sim.add_volume('Box', 'fake2')
b.mother = 'fake1'
b.size = [35 * cm, 35 * cm, 35 * cm]

# CT image #1
ct_odd = sim.add_volume('Image', 'ct_odd')
ct_odd.image = pathFile / '..' / 'data' / '10x10x10.mhd'
ct_odd.mother = 'fake2'
ct_odd.voxel_materials = [[0, 'G4_WATER']]
ct_odd.translation = [-2 * cm, 0, 0]
r = Rotation.from_euler('y', 25, degrees=True)
r = r * Rotation.from_euler('x', 35, degrees=True)
ct_odd.rotation = r.as_matrix()

# CT image #2
ct_even = sim.add_volume('Image', 'ct_even')
ct_even.image = pathFile / '..' / 'data' / '11x11x11.mhd'
ct_even.voxel_materials = ct_odd.voxel_materials
ct_even.translation = [-25 * cm, 0, 0]

# source from sphere
"""
    WARNING : if the source is a point and is centered with odd image, the source
    is at the intersection of 3 planes (8 voxels): then, lot of "navigation warning"
    from G4 occur. Not really clear why.
    So we move the source a bit. 
"""
source = sim.add_source('Generic', 's_odd')
source.particle = 'e-'
source.activity = 1000 * Bq / ui.number_of_threads
source.direction.type = 'iso'
source.mother = 'ct_odd'
source.position.translation = [10 * mm, 10 * mm, 10 * mm]
source.energy.mono = 1 * keV

# source from sphere
source = sim.add_source('Generic', 's_even')
source.particle = 'e-'
source.activity = 1000 * Bq / ui.number_of_threads
source.direction.type = 'iso'
source.mother = 'ct_even'
source.position.translation = [0 * mm, 0 * mm, 0 * mm]
source.energy.mono = 1 * keV

# source from spect
source = sim.add_source('Voxels', 'vox')
source.particle = 'e-'
source.activity = 4000 * Bq / ui.number_of_threads
source.image = pathFile / '..' / 'data' / 'five_pixels.mha'
source.direction.type = 'iso'
source.position.translation = [0 * mm, 0 * mm, 0 * mm]
source.energy.mono = 1 * keV
source.mother = 'ct_even'
source.img_coord_system = True

# cuts
p = sim.get_physics_user_info()
p.physics_list_name = 'G4EmStandardPhysics_option4'
p.enable_decay = False
c = p.production_cuts
c.world.gamma = 1 * mm
c.world.positron = 1 * mm
c.world.electron = 1 * mm
c.world.proton = 1 * m

# add dose actor
dose1 = sim.add_actor('DoseActor', 'dose1')
dose1.save = pathFile / '..' / 'output' / 'test021-odd-edep.mhd'
dose1.mother = 'ct_odd'
img = itk.imread(str(ct_odd.image))
img_info = gam.get_image_info(img)
dose1.dimension = img_info.size
dose1.spacing = img_info.spacing
dose1.img_coord_system = True

# add dose actor
dose2 = sim.add_actor('DoseActor', 'dose2')
dose2.save = pathFile / '..' / 'output' / 'test021-even-edep.mhd'
dose2.mother = 'ct_even'
img = itk.imread(str(ct_even.image))
img_info = gam.get_image_info(img)
dose2.dimension = img_info.size
dose2.spacing = img_info.spacing
dose2.img_coord_system = True

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
# stat.write('output_ref/stat021_ref.txt')

# test pixels in dose #1
d_odd = itk.imread(str(dose1.save))
s = itk.array_view_from_image(d_odd).sum()
v = d_odd.GetPixel([5, 5, 5])
diff = (s - v) / s
tol = 0.01
is_ok = diff < tol
diff *= 100
gam.print_test(is_ok, f'Image #1 (odd): {v:.2f} {s:.2f} -> {diff:.2f}%')

# test pixels in dose #1
d_even = itk.imread(str(dose2.save))
s = itk.array_view_from_image(d_even).sum()
v0 = d_even.GetPixel([5, 5, 5])
v1 = d_even.GetPixel([1, 5, 5])
v2 = d_even.GetPixel([1, 2, 5])
v3 = d_even.GetPixel([5, 2, 5])
v4 = d_even.GetPixel([6, 2, 5])
tol = 0.15
ss = v0 + v1 + v2 + v3 + v4


def t(s, v):
    diff = abs(s - v) / s
    b = diff < tol
    p = diff * 100.0
    gam.print_test(b, f'Image #2 (even) {s:.2f} vs {v:.2f}  -> {p:.2f}%')
    return b


is_ok = t(s, ss) and is_ok
is_ok = t(1.80, v0) and is_ok
is_ok = t(0.8, v1) and is_ok
is_ok = t(0.8, v2) and is_ok
is_ok = t(0.8, v3) and is_ok
is_ok = t(0.8, v4) and is_ok

stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'output_ref' / 'stat021_ref.txt')
stats_ref.counts.run_count = ui.number_of_threads
is_ok = gam.assert_stats(stat, stats_ref, 0.05) and is_ok

gam.test_ok(is_ok)

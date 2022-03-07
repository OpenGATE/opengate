#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_iec_phantom as gam_iec
import json
import itk
from scipy.spatial.transform import Rotation

paths = gam.get_default_test_paths(__file__, '')

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = 1
ui.check_volumes_overlap = False

# units
m = gam.g4_units('m')
cm = gam.g4_units('cm')
mm = gam.g4_units('mm')
MeV = gam.g4_units('MeV')
keV = gam.g4_units('keV')
Bq = gam.g4_units('Bq')
kBq = Bq * 1000

# world
sim.world.size = [3 * m, 3 * m, 3 * m]

# add a first iec phantom (analytical)
iec1 = gam_iec.add_phantom(sim, 'iec1')
iec1.translation = [40 * cm, 0 * cm, 0 * cm]
# rotation should have no effect
iec1.rotation = Rotation.from_euler('y', 33, degrees=True).as_matrix()

# to highlight the position, we change some volume with high density lead
v = sim.get_volume_user_info('iec1_sphere_37mm')
v.material = 'G4_LEAD_OXIDE'
v = sim.get_volume_user_info('iec1_center_cylinder_hole')
v.material = 'G4_LEAD_OXIDE'

# add a second iec phantom (voxelized)
iec2 = sim.add_volume('Image', 'iec2')
iec2.image = paths.output_ref / 'test032_iec.mhd'
iec2.material = 'G4_AIR'
iec2.translation = [-40 * cm, 0 * cm, 0 * cm]
iec2.dump_label_image = paths.output / 'test032_iec_label.mhd'
labels = json.loads(open(paths.output_ref / 'test032_labels.json').read())
iec2.voxel_materials = []
for l in labels:
    mat = 'IEC_PLASTIC'
    if 'capillary' in l:
        mat = 'G4_WATER'
    if 'cylinder_hole' in l:
        mat = 'G4_LUNG_ICRP'
    if 'interior' in l:
        mat = 'G4_WATER'
    if 'sphere' in l:
        mat = 'G4_WATER'
    if 'world' in l:
        mat = 'G4_AIR'
    if 'shell' in l:
        mat = 'IEC_PLASTIC'
    if 'sphere_37mm' in l:
        mat = 'G4_LEAD_OXIDE'
    if 'center_cylinder_hole' in l:
        mat = 'G4_LEAD_OXIDE'
    m = [labels[l], labels[l] + 1, mat]
    iec2.voxel_materials.append(m)

pMin, pMax = gam.get_volume_bounding_limits(sim, 'iec1')
print(f'pMin and pMax of iec1', pMin, pMax)

# the origin of iec1 is different from the origin of iec2
# we create fake images to be able to convert from
# the image coordinate space to iec1 or iec2
# Coordinate system of iec1 is pMin (the extend)
# Coordinate system of iec2 is the center of the image bounding box
img = itk.imread(str(iec2.image))
fake1 = gam.create_image_like(img)
pMin = gam.vec_g4_as_np(pMin)
fake1.SetOrigin(pMin)

fake2 = gam.create_image_like(img)
info = gam.get_image_info(fake2)
origin = -info.size * info.spacing / 2.0 + info.spacing / 2.0
fake2.SetOrigin(origin)

# sources
activity = 10 * kBq
for i in range(1, 3):
    source = sim.add_source('Generic', f'src{i}')
    source.mother = f'iec{i}'
    source.energy.mono = 100 * MeV
    source.particle = 'proton'
    source.position.type = 'sphere'
    source.position.radius = 10 * mm
    # WARNING the center of the volume is different in the image (iec2)
    # and in the analytical phantom (iec1)
    p = [31 * mm, 33 * mm, 36 * mm]
    if i == 1:
        p = gam.transform_images_point(p, img, fake1)
    else:
        p = gam.transform_images_point(p, img, fake2)
    source.position.translation = p
    source.activity = activity
    source.direction.type = 'iso'

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'stats')
stats.track_types_flag = True

# add dose actor
for i in range(1, 3):
    dose = sim.add_actor('DoseActor', f'dose{i}')
    dose.save = paths.output / f'test032_iec{i}_edep.mhd'
    dose.mother = f'iec{i}'
    dose.dimension = [100, 100, 100]
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    # translate the iec1 to have the exact same dose origin
    # (only needed to perform the assert_image test)
    if i == 1:
        dose.translation = [0 * mm, 35 * mm, 0 * mm]
    dose.img_coord_system = True

# initialize & start
sim.initialize()
sim.start()

# stats
stats = sim.get_actor('stats')
print(stats)

# compare edep map
is_ok = gam.assert_images(paths.output / 'test032_iec1_edep.mhd',
                          paths.output / 'test032_iec2_edep.mhd',
                          stats, tolerance=79, axis='x')

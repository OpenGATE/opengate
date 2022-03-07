#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_iec_phantom as gam_iec
import itk
import json

paths = gam.get_default_test_paths(__file__, '')

# create the simulation
sim = gam.Simulation()

# shhhht !
gam.log.setLevel(gam.NONE)

# world
m = gam.g4_units('m')
sim.world.size = [1 * m, 1 * m, 1 * m]

# add a iec phantom
iec = gam_iec.add_phantom(sim)

# initialize only (no source but no start).
# initialization is needed because it builds the hierarchy of G4 volumes
# that are needed by the "voxelize" function
sim.initialize()

# create an empty image with the size (extent) of the volume
# add one pixel margin
image = gam.create_image_with_volume_extent(sim, iec.name, spacing=[3, 3, 3], margin=1)
info = gam.get_image_info(image)
print(f'Image : {info.size} {info.spacing} {info.origin}')

# voxelized a volume
print('Starting voxelization ...')
labels, image = gam.voxelize_volume(sim, iec.name, image)
print(f'Output labels: {labels}')

# write labels
lf = str(paths.output / 'test032_labels_3mm.json')
outfile = open(lf, 'w')
json.dump(labels, outfile, indent=4)

# write image
f = paths.output / 'test032_iec_3mm.mhd'
print(f'Write image {f}')
itk.imwrite(image, str(f))

# do the same with 1 mm spacing

# create an empty image with the size (extent) of the volume
# add one pixel margin
image = gam.create_image_with_volume_extent(sim, iec.name, spacing=[1, 1, 1], margin=1)
info = gam.get_image_info(image)
print(f'Image : {info.size} {info.spacing} {info.origin}')

# voxelized a volume
print('Starting voxelization ...')
labels, image = gam.voxelize_volume(sim, iec.name, image)
print(f'Output labels: {labels}')

# write labels
lf = str(paths.output / 'test032_labels.json')
outfile = open(lf, 'w')
json.dump(labels, outfile, indent=4)

# write image
f = paths.output / 'test032_iec.mhd'
print(f'Write image {f}')
itk.imwrite(image, str(f))

# read and compare labels
gam.warning('\nDifference labels')
ref_labels = open(paths.output_ref / 'test032_labels.json').read()
ref_labels = json.loads(ref_labels)
added, removed, modified, same = gam.dict_compare(ref_labels, labels)
is_ok = len(added) == 0 and len(removed) == 0 and len(modified) == 0
gam.print_test(is_ok, f'Labels comparisons, added:    {added}')
gam.print_test(is_ok, f'Labels comparisons, removed:  {removed}')
gam.print_test(is_ok, f'Labels comparisons: modified: {modified}')

# compare images
gam.warning('\nDifference with ref image')
is_ok = gam.assert_images(f, paths.output_ref / 'test032_iec.mhd', stats=None, tolerance=0.01) and is_ok

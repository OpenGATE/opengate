#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test043_garf_helpers import *
import itk
import numpy as np

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_seed = 'auto'

# activity
activity = 4e6 * Bq

# add a material database
sim.add_material_database(paths.gate_data / 'GateMaterials.db')

# init world
sim_set_world(sim)

# fake spect head
spect_length = 18 * cm
# spect_radius = 25 * cm
# spect_psd_position = 8.41 * cm
# spect_translation = spect_radius + spect_psd_position
spect_translation = 15 * cm
SPECThead = sim.add_volume('Box', 'SPECThead')
SPECThead.size = [57.6 * cm, 44.6 * cm, spect_length]
SPECThead.translation = [0, 0, -spect_translation]
SPECThead.material = 'G4_AIR'
SPECThead.color = [1, 0, 1, 1]

# detector input plane
detPlane = sim_set_detector_plane(sim, SPECThead.name)

# physics
sim_phys(sim)

# sources
sim_source_test(sim, 'fake_not_used', activity)

# arf actor
arf = sim.add_actor('ARFActor', 'arf')
arf.mother = detPlane.name
arf.batch_size = 2e5
arf_detector = gam.ARFDetector(arf)  ## need initialize and apply
arf_detector.pth_filename = paths.gate_data / 'pth' / 'arf_Tc99m.pth'
#arf_detector.pth_filename = 'bidon-v1.pth'
# arf_detector.pth_filename = 'bidon-v2.pth'
arf.arf_detector = arf_detector

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'stats')
s.track_types_flag = True

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# print results at the end
stat = sim.get_actor('stats')
print(stat)

# build the final image
print('get img', arf_detector.data_img.shape)
# set the first channel to zero
arf_detector.data_img[0, :] = 0
gam.DD(stat.counts.event_count)
# arf_detector.data_img /= stat.counts.event_count
# arf_detector.data_img /= arf_detector.g4_actor.fCurrentNumberOfHits
# arf_detector.data_img /= stat.counts.event_count
img = itk.image_from_array(arf_detector.data_img)

# origin like in gate
spacing = [4.41806 * mm, 4.41806 * mm, 1 * mm]
img.SetSpacing(spacing)
origin = np.divide(spacing, 2.0)
gam.DD(origin)
img.SetOrigin(origin)

# origin like in gam gate
"""p = arf_detector.param
spacing = np.array(arf_detector.param.spacing)
gam.DD(spacing)
spacing[2] = 63.333333  ## fixme see analog
img.SetSpacing(spacing)
size = np.array(p.size)
size[0] = p.size[2]
size[2] = p.size[0]
origin = -size / 2.0 * spacing + spacing / 2.0
origin[2] = -213.33333 # fixme why ?
gam.DD(origin)
img.SetOrigin(origin)"""

filename = paths.output / 'test043_projection.mhd'
InputImageType = itk.Image[itk.D, 3]
OutputImageType = itk.Image[itk.F, 3]
castImageFilter = itk.CastImageFilter[InputImageType, OutputImageType].New()
castImageFilter.SetInput(img)
castImageFilter.Update()
img = castImageFilter.GetOutput()
itk.imwrite(img, str(filename))

# ----------------------------------------------------------------------------------------------------------------
# tests
print()
gam.warning('Tests stats file')
stats_ref = gam.read_stat_file(paths.gate_output / 'stats_analog.txt')
is_ok = gam.assert_stats(stat, stats_ref, 0.03)

'''print()
is_ok = gam.assert_images(filename,
                          paths.gate_output / 'projection.mhd',
                          stat, tolerance=10, ignore_value=0, axis='x') and is_ok'''

print()
is_ok = gam.assert_images(filename,
                          # paths.gate_output / 'projection_analog.mhd',
                          paths.output / 'test043_projection_analog.mhd',
                          stat, tolerance=10, ignore_value=0, axis='x') and is_ok

print()
print('profile compare : ')
print(f'garf_compare_image_profile {paths.gate_output / "projection_analog.mhd"} {filename} -w 3')
print(f'garf_compare_image_profile {paths.gate_output / "projection_analog.mhd"} {filename} -w 3 -s 75')

gam.delete_run_manager_if_needed(sim)
gam.test_ok(is_ok)

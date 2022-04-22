#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
from box import Box
from contrib.dose_rate_helpers import dose_rate

paths = gam.get_default_test_paths(__file__, '')

# set param
param = Box()
param.ct_image = str(paths.data / '29_CT_5mm_crop.mhd')
param.activity_image = str(paths.data / 'activity_test_crop_4mm.mhd')
param.radionuclide = 'Lu177'
param.activity_bq = 1e5
param.number_of_threads = 1
param.visu = False
param.output_folder = str(paths.output / 'output_test035')

# Create the simu
sim = dose_rate(param)

# change source to alpha to get quick high local dose
source = sim.get_source_user_info('vox')
source.particle = 'alpha'
MeV = gam.g4_units('MeV')
source.energy.mono = 1 * MeV

# run
sim.initialize()
sim.start()

# print results
gam.warning(f'Check stats')
stats = sim.get_actor('Stats')
# stats.write(param.output_folder / 'stats.txt')
print(stats)
stats_ref = gam.read_stat_file(paths.output_ref / 'output_test035' / 'stats.txt')
is_ok = gam.assert_stats(stats, stats_ref, 0.10)

gam.warning(f'Check dose')
h = sim.get_actor('dose')
print(h)
is_ok = gam.assert_images(h.user_info.save,
                          paths.output_ref / 'output_test035' / 'edep.mhd',
                          stats, tolerance=35, ignore_value=0) and is_ok

gam.test_ok(is_ok)

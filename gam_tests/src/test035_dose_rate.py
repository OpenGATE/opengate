#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
from box import Box
from contrib.dose_rate_helpers import dose_rate

paths = gam.get_default_test_paths(__file__, '')
dr_data = paths.data / 'dose_rate_data'

# set param
gcm3 = gam.g4_units('g/cm3')
param = Box()
param.ct_image = str(dr_data / '29_CT_5mm_crop.mhd')
param.table_mat = str(dr_data / 'Schneider2000MaterialsTable.txt')
param.table_density = str(dr_data / 'Schneider2000DensitiesTable.txt')
param.activity_image = str(dr_data / 'activity_test_crop_4mm.mhd')
param.radionuclide = 'Lu177'
param.activity_bq = 1e6
param.number_of_threads = 1
param.visu = False
param.verbose = True
param.density_tolerance_gcm3 = 0.05
param.output_folder = str(paths.output / 'output_test035')

# Create the simu
# Note that the returned sim object can be modified to change source or cuts or whatever other parameters
sim = dose_rate(param)

# Change source to alpha to get quick high local dose
source = sim.get_source_user_info('vox')
source.particle = 'alpha'
MeV = gam.g4_units('MeV')
source.energy.mono = 1 * MeV

print('Phys list cuts:')
print(sim.physics_manager.dump_cuts())

# run
sim.initialize()
sim.start()

# print results
print()
gam.warning(f'Check stats')
stats = sim.get_actor('Stats')
stats.write(param.output_folder / 'stats035.txt')
print(stats)
stats_ref = gam.read_stat_file(paths.output_ref / 'output_test035' / 'stats.txt')
is_ok = gam.assert_stats(stats, stats_ref, 0.10)

# dose comparison
print()
gam.warning(f'Check dose')
h = sim.get_actor('dose')
print(h)
is_ok = gam.assert_images(h.user_info.save,
                          paths.output_ref / 'output_test035' / 'edep.mhd',
                          stats, tolerance=15, ignore_value=0) and is_ok

gam.test_ok(is_ok)

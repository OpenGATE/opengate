#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test028_ge_nm670_spect_acc_angle_base import *
import itk
import numpy as np

paths = gam.get_common_test_paths(__file__, 'gate_test028_ge_nm670_spect')

# create the simulation
sim = gam.Simulation()

# main description
spect, proj = create_spect_simu(sim, paths, number_of_threads=2, activity_kBq=1000)

ui = sim.user_info
# ui.force_multithread_mode = True
ui.running_verbose_level = 0  # 50 for event
ui.random_engine = 'MixMaxRng'
ui.visu = False
print(ui)

# rotate spect
cm = gam.g4_units('cm')
psd = 6.11 * cm
p = [0, 0, -(15 * cm + psd)]
spect.translation, spect.rotation = gam.get_transform_orbiting(p, 'y', 15)
print('translation', spect.translation)

sim.initialize()
#sim.apply_g4_command("/run/eventModulo 5000 1")
sim.start()

# check
# test_spect_proj(sim, paths, proj)

b1 = gam.get_skipped_particles(sim, 'beam1')
b2 = gam.get_skipped_particles(sim, 'beam2')
b3 = gam.get_skipped_particles(sim, 'beam3')

print(f'Skipped particles b2 = {b1}')
print(f'Skipped particles b1 = {b2}')
print(f'Skipped particles b3 = {b3}')

# stat
gam.warning('Compare stats')
stats = sim.get_actor('Stats')
print(stats)
stats_ref = gam.read_stat_file(paths.gate_output_ref / 'stat4.txt')
print(f'Number of runs was {stats.counts.run_count}. Set to 1 before comparison')
stats.counts.run_count = 1  # force to 1
print(f'Number of steps was {stats.counts.step_count}, force to the same value (because of angle acceptance). ')
stats.counts.step_count = stats_ref.counts.step_count  # force to id
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.07)

# read image and force change the offset to be similar to old Gate
gam.warning('Compare projection image')
img = itk.imread(str(paths.output / 'proj028_colli.mhd'))
spacing = np.array(proj.spacing)
origin = spacing / 2.0
origin[2] = 0.5
spacing[2] = 1
img.SetSpacing(spacing)
img.SetOrigin(origin)
itk.imwrite(img, str(paths.output / 'proj028_colli_offset.mhd'))
# There are not enough event to make a proper comparison, so the tol is very high
is_ok = gam.assert_images(paths.output / 'proj028_colli_offset.mhd',
                          paths.gate_output_ref / 'projection4.mhd',
                          stats, tolerance=85   , ignore_value=0, axis='x') and is_ok

gam.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test028_ge_nm670_spect_base2 import *

paths = gam.get_common_test_paths(__file__, 'gate_test028_ge_nm670_spect')

# create the simulation
sim = gam.Simulation()

# main description
spect, proj = create_spect_simu(sim, paths, number_of_threads=1, activity_kBq=300)

ui = sim.user_info
ui.running_verbose_level = 0  # 50 for event

# rotate spect
cm = gam.g4_units('cm')
psd = 6.11 * cm
p = [0, 0, -(15 * cm + psd)]
spect.translation, spect.rotation = gam.get_transform_orbiting(p, 'y', 0)
print('translation', spect.translation)

sim.initialize()
sim.start()

# check
# test_spect_proj(sim, paths, proj)

beam1 = sim.get_source('beam1')
print(f'Skipped particles = {beam1.fSkippedParticles}')

# stat
gam.warning('Compare stats')
stats = sim.get_actor('Stats')
print(stats)
print(f'Number of runs was {stats.counts.run_count}. Set to 1 before comparison')
stats.counts.run_count = 1  # force to 1
stats_ref = gam.read_stat_file(paths.gate_output_ref / 'stat4.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.07)

# read image and force change the offset to be similar to old Gate
img = itk.imread(str(paths.output / 'proj028_colli.mhd'))
spacing = np.array(proj.spacing)
origin = spacing / 2.0
origin[2] = 0.5
spacing[2] = 1
img.SetSpacing(spacing)
img.SetOrigin(origin)
itk.imwrite(img, str(paths.output / 'proj028_colli_offset.mhd'))

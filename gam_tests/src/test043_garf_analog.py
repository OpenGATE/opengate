#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test043_garf_helpers import *
import contrib.spect_ge_nm670 as gam_spect
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
ui.number_of_threads = 1
colli = 'lehr'

# units
activity = 1e6 * Bq / ui.number_of_threads

# world
sim_set_world(sim)

# spect head
spect = gam_spect.add_ge_nm67_spect_head(sim, 'spect', collimator_type=colli, debug=ui.visu)
spect_translation = 15 * cm
spect.translation = [0, 0, -spect_translation]
crystal_name = f'{spect.name}_crystal'

# physics
sim_phys(sim)

# sources
sim_source_test(sim, activity)

# digitizer
channels = [
    {'name': f'spectrum_{spect.name}', 'min': 0 * keV, 'max': 160 * keV},
    {'name': f'scatter_{spect.name}', 'min': 114 * keV, 'max': 126 * keV},
    {'name': f'peak140_{spect.name}', 'min': 126 * keV, 'max': 154 * keV}
]
proj = gam_spect.add_digitizer(sim, crystal_name, channels)
proj.spacing = [4.41806 * mm, 4.41806 * mm]
proj.output = paths.output / 'test043_projection_analog.mhd'

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

# dump the output image with offset like in old gate (for comparison)
print('We change the spacing/origin to be compared to the old gate')
proj = sim.get_actor(f'Projection_{crystal_name}')
spacing = np.array([4.41806 * mm, 4.41806 * mm, 1])
proj.output_image.SetSpacing(spacing)
proj.output_image.SetOrigin(spacing / 2.0)
fn = str(proj.user_info.output).replace('.mhd', '_offset.mhd')
itk.imwrite(proj.output_image, fn)

# ----------------------------------------------------------------------------------------------------------------
# tests
print()
gam.warning('Tests stats file')
stats_ref = gam.read_stat_file(paths.gate_output / 'stats_analog.txt')
stat.counts.run_count = 1  # force to one run (ref only have 1 thread)
is_ok = gam.assert_stats(stat, stats_ref, 0.01)

print()
gam.warning('Tests projection (old gate)')
is_ok = gam.assert_images(paths.gate_output / 'projection_analog.mhd',
                          fn,
                          stat, tolerance=70, ignore_value=0, axis='x') and is_ok

print()
gam.warning('Tests projection (new)')
is_ok = gam.assert_images(paths.output_ref / 'test043_projection_analog.mhd',
                          proj.user_info.output,
                          stat, tolerance=70, ignore_value=0, axis='x') and is_ok

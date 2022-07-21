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
ui.number_of_threads = 5
colli = 'lehr'

# units
activity = 4e6 * Bq / ui.number_of_threads

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
sim_source_test(sim, spect.name, activity)

# digitizer
channels = [
    {'name': f'empty_{spect.name}', 'min': 0 * keV, 'max': 1 * keV},
    {'name': f'scatter_{spect.name}', 'min': 114 * keV, 'max': 126 * keV},
    {'name': f'peak140_{spect.name}', 'min': 126 * keV, 'max': 154 * keV}
]
proj = gam_spect.add_digitizer(sim, crystal_name, channels)
proj.spacing = [4.41806 * mm, 4.41806 * mm]
proj.output = ''

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

# image with offset like old gate
proj = sim.get_actor(f'Projection_{crystal_name}')
output = str(paths.output / 'test043_projection_analog.mhd')
spacing = np.array([4.41806 * mm, 4.41806 * mm, 1])
proj.image.SetSpacing(spacing)
proj.image.SetOrigin(spacing / 2.0)
itk.imwrite(proj.image, output)

# image with offset like gate

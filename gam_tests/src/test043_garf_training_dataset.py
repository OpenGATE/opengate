#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test043_garf_helpers import *
import contrib.spect_ge_nm670 as gam_spect

paths = gam.get_default_test_paths(__file__, 'gate_test043_garf')

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.number_of_threads = 1
ui.visu = False
ui.random_seed = 'auto'

# activity
activity = 1e5 * Bq / ui.number_of_threads

# world size
sim_set_world(sim)

# spect head
spect = gam_spect.add_ge_nm67_spect_head(sim, 'spect', collimator_type='lehr', debug=ui.visu)
distance_to_crystal = gam_spect.distance_to_center_of_crystal(sim, 'spect')
crystal_name = f'{spect.name}_crystal'

# detector input plane
detPlane = sim_set_detector_plane(sim, spect.name)

# physics
sim_phys(sim)

# source
s1 = sim.add_source('Generic', 's1')
s1.particle = 'gamma'
s1.activity = activity
s1.position.type = 'disc'
s1.position.radius = 57.6 * cm / 4  # FIXME why ???
s1.position.translation = [0, 0, 12 * cm]
s1.direction.type = 'iso'
s1.energy.type = 'range'
s1.energy.min_energy = 0.01 * MeV
s1.energy.max_energy = 0.154 * MeV
s1.direction.acceptance_angle.volumes = [detPlane.name]
s1.direction.acceptance_angle.intersection_flag = True

# digitizer
channels = [
    {'name': f'scatter_{spect.name}', 'min': 114 * keV, 'max': 126 * keV},
    {'name': f'peak140_{spect.name}', 'min': 126 * keV, 'max': 154 * keV}
]
cc = gam_spect.add_digitizer_energy_windows(sim, crystal_name, channels)

# arf actor for building the training dataset
arf = sim.add_actor('ARFTrainingDatasetActor', 'ARF (training)')
arf.mother = detPlane.name
# arf.output = paths.output / 'test043_arf_training_dataset_rr100_low.root'
# arf.output = paths.output / 'test043_arf_training_dataset_rr300.root'
# arf.output = paths.output / 'test043_arf_training_dataset_rr30.root'
arf.output = paths.output / 'test043_arf_training_dataset.root'
arf.energy_windows_actor = cc.name
arf.russian_roulette = 100

dpz = detPlane.translation[2]
d = dpz + distance_to_crystal
print('dpz', dpz, d)  # 283.675 ???

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'stats')
s.track_types_flag = True
s.output = str(arf.output).replace('.root', '_stats.txt')

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# print results at the end
stat = sim.get_actor('stats')
print(stat)
skip = gam.get_source_skipped_particles(sim, 's1')
print(f'Nb of skip particles {skip}  {(skip / stat.counts.event_count) * 100:.2f}%')

# ----------------------------------------------------------------------------------------------------------------
gam.warning('Compare stats')
stats_ref = gam.read_stat_file(paths.output_ref / s.output)
is_ok = gam.assert_stats(stat, stats_ref, 0.01)

gam.warning('Compare root')
checked_keys = [{'k1': 'E', 'k2': 'E', 'tol': 0.005, 'scaling': 1},
                {'k1': 'Theta', 'k2': 'Theta', 'tol': 4.5, 'scaling': 1},
                {'k1': 'Phi', 'k2': 'Phi', 'tol': 3.5, 'scaling': 1},
                {'k1': 'window', 'k2': 'window', 'tol': 0.004, 'scaling': 1}]
is_ok = gam.compare_root2(paths.output_ref / 'test043_arf_training_dataset.root',
                          arf.output, 'ARF (training)', 'ARF (training)',
                          checked_keys, paths.output / 'test043_training_dataset.png', n_tol=14) and is_ok

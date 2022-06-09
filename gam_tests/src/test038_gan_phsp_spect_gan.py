#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.spect_ge_nm670 as gam_spect
import contrib.phantom_nema_iec_body as gam_iec
import gatetools.phsp as phsp
import uproot
import numpy as np
import time
import matplotlib.pyplot as plt
import os

paths = gam.get_default_test_paths(__file__, 'gate_test038_gan_phsp_spect')

# create the simulation
sim = gam.Simulation()

# units
m = gam.g4_units('m')
cm = gam.g4_units('cm')
cm3 = gam.g4_units('cm3')
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')
BqmL = Bq / cm3
sec = gam.g4_units('second')
deg = gam.g4_units('deg')
kBq = 1000 * Bq
MBq = 1000 * kBq

# main parameters
ui = sim.user_info
ui.check_volumes_overlap = True
ui.number_of_threads = 1
ac = 1e3 * BqmL
ui.visu = False
colli_flag = not ui.visu

# world size
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]
world.material = 'G4_AIR'

# iec phantom (needed for cond) FIXME
iec_phantom = gam_iec.add_phantom(sim)

# cylinder of the phase space, for visualisation only
"""cyl = sim.add_volume('Sphere', 'phase_space_cylinder')
cyl.rmin = 210 * mm
cyl.rmax = 211 * mm
cyl.color = [1, 1, 1, 1]
cyl.material = 'G4_AIR'"""

# test phase space to check with reference
cyl = sim.add_volume('Sphere', 'phase_space_cylinder')
cyl.rmin = 215 * mm
cyl.rmax = 216 * mm
cyl.color = [1, 1, 1, 1]
cyl.material = 'G4_AIR'

# spect head
distance = 30 * cm
psd = 6.11 * cm
p = [0, 0, -(distance + psd)]
spect1 = gam_spect.add_ge_nm67_spect_head(sim, 'spect1', collimator=colli_flag, debug=False)
spect1.translation, spect1.rotation = gam.get_transform_orbiting(p, 'x', 180)

# spect head (debug mode = very small collimator)
# spect2 = gam_spect.add_ge_nm67_spect_head(sim, 'spect2', collimator=colli_flag, debug=False)
# spect2.translation, spect2.rotation = gam.get_transform_orbiting(p, 'x', 0)

# physic list
sim.set_cut('world', 'all', 1 * mm)

# init for cond
spheres_diam = [10, 13, 17, 22, 28, 37]
# spheres_diam = [37]
# spheres_activity_concentration = [ac] * len(spheres_diam)
spheres_activity_concentration = [ac * 6, ac * 5, ac * 4, ac * 3, ac * 2, ac]
spheres_activity_ratio = []
spheres_activity = []
spheres_centers = []
for diam, ac in zip(spheres_diam, spheres_activity_concentration):
    d = f'{(diam / mm):.0f}mm'
    vname = f'iec_sphere_{d}'
    v = sim.get_volume_user_info(vname)
    # print(v)
    s = sim.get_solid_info(v)
    # print(s)
    center = v.translation
    spheres_centers.append(center)
    volume = s.cubic_volume
    activity = ac * volume
    print(f'Sphere {diam}: {str(center):<30} {s.cubic_volume / cm3:7.3f} cm3 '
          f'{activity / Bq:7.0f} Bq  {ac / BqmL:7.1f} BqmL')
    spheres_activity.append(activity)

total_activity = sum(spheres_activity)
print(f'Total activity {total_activity / Bq:.0f} Bq')
for activity in spheres_activity:
    spheres_activity_ratio.append(activity / total_activity)
print('Activity ratio ', spheres_activity_ratio, sum(spheres_activity_ratio))

# will store all conditional info (position, direction)
all_cond = None


def gen_cond(n):
    # start = time.time()
    i = 0
    cond = None
    # print()
    for diam, center, r in zip(spheres_diam, spheres_centers, spheres_activity_ratio):
        radius = diam / 2.0
        # approximate -> if the last one we complete to reach n
        if i == len(spheres_diam) - 1:
            m = n - len(cond)
            # print(f'Last one {m} instead of {int(round(n * r))}')
        else:
            m = int(round(n * r))
        conds = gam_iec.generate_pos_dir_sphere(center, radius, m)
        if i == 0:
            cond = conds
        else:
            cond = np.vstack((cond, conds))
        # print('generate cond ', radius, m, cond.shape)
        i += 1

    # shuffle
    # it seems that permutation is much faster than shuffle
    # (checked 2022/06/047 on osx)
    # https://github.com/numpy/numpy/issues/11013
    # sstart = time.time()
    # np.random.shuffle(cond)
    # send = time.time()
    # print(f'shuffle 1 {send - sstart:0.4f} sec')
    # sstart = time.time()
    cond.take(np.random.permutation(cond.shape[0]), axis=0)
    # send = time.time()
    # print(f'shuffle 2 {send - sstart:0.4f} sec')

    # end = time.time()
    # print(f'cond done in {end - start:0.4f} sec')
    # print()

    global all_cond
    if all_cond is None:
        all_cond = cond
    else:
        all_cond = np.column_stack((all_cond, cond))

    return cond


# GAN source
gsource = sim.add_source('GAN', 'gaga')
gsource.particle = 'gamma'
# gsource.mother = iec_phantom.name
gsource.mother = f'{iec_phantom.name}_interior'  # FIXME
gsource.activity = total_activity
gsource.pth_filename = paths.gate / 'pth1' / 'test001_GP_0GP_10_50000.pth'
gsource.position_keys = ['PrePosition_X', 'PrePosition_Y', 'PrePosition_Z']
gsource.direction_keys = ['PreDirection_X', 'PreDirection_Y', 'PreDirection_Z']
gsource.energy_key = 'KineticEnergy'
gsource.weight_key = None
gsource.time_key = 'TimeFromBeginOfEvent'
gsource.time_relative = True
gsource.batch_size = 8.6e4
gsource.verbose_generator = True
# it is possible to define another generator
# gsource.generator = gam.GANSourceDefaultGenerator(gsource)
gen = gam.GANSourceConditionalGenerator(gsource)
gen.generate_condition = gen_cond
gsource.generator = gen

# add stat actor
stat = sim.add_actor('SimulationStatisticsActor', 'Stats')
stat.output = paths.output / 'test038_gan_stats.txt'

# add default digitizer (it is easy to change parameters if needed)
gam_spect.add_ge_nm670_spect_simplified_digitizer(sim, 'spect1_crystal', paths.output / 'test038_gan_proj.mhd')
# gam_spect.add_ge_nm670_spect_simplified_digitizer(sim, 'spect2_crystal', paths.output / 'test033_proj_2.mhd')
singles_actor = sim.get_actor_user_info(f'Singles_spect1_crystal')
singles_actor.output = paths.output / 'test038_gan_singles.root'

# motion of the spect, create also the run time interval
"""heads = [spect1]  # [spect1, spect2]

# create a list of run (total = 1 second)
n = 1
sim.run_timing_intervals = gam.range_timing(0, 1 * sec, n)

for head in heads:
    motion = sim.add_actor('MotionVolumeActor', f'Move_{head.name}')
    motion.mother = head.name
    motion.translations, motion.rotations = \
        gam.volume_orbiting_transform('x', 0, 180, n, head.translation, head.rotation)
    motion.priority = 5"""

phsp_actor = sim.add_actor('PhaseSpaceActor', 'phsp')
phsp_actor.mother = cyl.name
phsp_actor.attributes = ['KineticEnergy', 'PrePosition',
                         'PreDirection', 'GlobalTime']
phsp_actor.output = paths.output / 'test038_gan_phsp.root'

# ----------------------------------------------------------------------------------------------
# go
# ui.running_verbose_level = gam.EVENT
sim.initialize()
sim.start()

# ----------------------------------------------------------------------------------------------
# print stats
print()
gam.warning(f'Check stats')
s = sim.get_source('gaga')
print(f'Source, nb of E<=0: {s.fNumberOfNegativeEnergy}')
stats = sim.get_actor('Stats')
print(stats)
print('!!! Steps cannot be compared => multiplied by 3.66')
stats.counts.step_count *= 3.66
stats_ref = gam.read_stat_file(paths.output / 'test038_ref_stats.txt')
is_ok = gam.assert_stats(stats, stats_ref, 0.10)

# save conditional for checking with reference cond
keys = ['EventPosition_X', 'EventPosition_Y', 'EventPosition_Z',
        'TrackVertexMomentumDirection_X', 'TrackVertexMomentumDirection_Y', 'TrackVertexMomentumDirection_Z']
phsp.save_npy(paths.output / 'test038_gan_phsp_cond.npy', all_cond, keys)

# ----------------------------------------------------------------------------------------------
# compare conditional
# less particle in the ref because conditional data are store
# when exit (not absorbed)
print()
gam.warning(f'Check conditions (position, direction)')
root_ref = paths.output / 'test038_ref_phsp.root'
hits1 = uproot.open(root_ref)
branch = hits1.keys()[0]
print('Branch name:', branch)
hits1 = hits1[branch]
hits1_n = hits1.num_entries
hits1 = hits1.arrays(library="numpy")
root_gan = paths.output / 'test038_gan_phsp_cond.npy'
hits2, hits2_keys, hits2_n = phsp.load(root_gan)
tols = [10] * len(keys)
tols = [0.4, 0.6, 0.1, 0.02, 0.02, 0.02]
scalings = [1] * len(keys)
is_ok = gam.compare_trees(hits1, list(hits1.keys()),
                          hits2, list(hits2_keys),
                          keys, keys, tols, scalings, scalings,
                          True) and is_ok
# figure
img_filename = paths.output / 'test038_cond.png'
plt.suptitle(f'Values: ref {os.path.basename(root_ref)} {os.path.basename(root_gan)} '
             f'-> {hits1_n} vs {hits2_n}')
plt.savefig(img_filename)
print(f'Figure in {img_filename}')

# ----------------------------------------------------------------------------------------------
# compare output phsp
print()
gam.warning(f'Check output phsp')
ref_file = str(phsp_actor.output).replace('gan', 'ref')
hc_file = phsp_actor.output
checked_keys = ['GlobalTime', 'KineticEnergy', 'PrePosition_X', 'PrePosition_Y', 'PrePosition_Z',
                'PreDirection_X', 'PreDirection_Y', 'PreDirection_Z']
scalings = [1] * len(checked_keys)
scalings[0] = 1e-9  # time in ns
tols = [0.003, 0.01, 1.5, 1.5, 1.5, 0.03, 0.03, 0.03]
print(scalings, tols)
is_ok = gam.compare_root3(ref_file, hc_file, "phsp", "phsp",
                          checked_keys, checked_keys, tols, scalings, scalings,
                          paths.output / 'test038_phsp.png') and is_ok

# ----------------------------------------------------------------------------------------------
# compare hits
print()
gam.warning(f'Check singles')
ref_file = str(singles_actor.output).replace('gan', 'ref')
hc_file = singles_actor.output
checked_keys = ['GlobalTime', 'TotalEnergyDeposit', 'PostPosition_X', 'PostPosition_Y', 'PostPosition_Z']
scalings = [1] * len(checked_keys)
scalings[0] = 1e-9  # time in ns
tols = [0.03, 0.02, 4, 4, 4]
print(scalings, tols)
is_ok = gam.compare_root3(ref_file, hc_file, "Singles_spect1_crystal", "Singles_spect1_crystal",
                          checked_keys, checked_keys, tols, scalings, scalings,
                          paths.output / 'test038_singles.png') and is_ok

# ----------------------------------------------------------------------------------------------
print()
gam.warning('WARNING on osx, need to del the RM, otherwise, GIL bug')
'''
Fatal Python error: take_gil: PyMUTEX_LOCK(gil->mutex) failed
Python runtime state: finalizing (tstate=0x142604960)
'''
del sim.g4_RunManager
print('RunManager deleted.')

# this is the end, my friend
gam.test_ok(is_ok)

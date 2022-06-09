#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.spect_ge_nm670 as gam_spect
import contrib.phantom_nema_iec_body as gam_iec
import uproot

paths = gam.get_default_test_paths(__file__, '')

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
# on mac, about 1 min for 1e5
ac = 1e6 * BqmL
ac = 1e3 * BqmL
ui.visu = False
colli_flag = not ui.visu
if ui.visu:
    ac = 1 * BqmL  # per mL
    ui.number_of_threads = 1

# world size
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]
world.material = 'G4_AIR'

# iec phantom
iec_phantom = gam_iec.add_phantom(sim)

# test phase space
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
# sim.set_cut('spect1_crystal', 'all', 1 * mm)
# sim.set_cut('spect2_crystal', 'all', 1 * mm)

# source sphere
gam_iec.add_spheres_sources(sim, 'iec', 'source1',
                            [10, 13, 17, 22, 28, 37],
                            # [37],
                            [ac * 6, ac * 5, ac * 4, ac * 3, ac * 2, ac], verbose=True)
# [ac], verbose=True)

# with acceptance angle (?) # FIXME
sources = sim.source_manager.user_info_sources
for source in sources.values():
    print(source)
    source.particle = 'gamma'
    source.energy.type = 'mono'
    source.energy.mono = 140.5 * keV

# background source 1:10 ratio with sphere
# bg = gam_iec.add_background_source(sim, 'iec', 'source_bg', ac / 10, verbose=True)

# add stat actor
stat = sim.add_actor('SimulationStatisticsActor', 'Stats')
stat.output = paths.output / 'test038_ref_stats.txt'

# add default digitizer (it is easy to change parameters if needed)
gam_spect.add_ge_nm670_spect_simplified_digitizer(sim, 'spect1_crystal', paths.output / 'test038_ref_proj.mhd')
# gam_spect.add_ge_nm670_spect_simplified_digitizer(sim, 'spect2_crystal', paths.output / 'test033_proj_2.mhd')
singles_actor = sim.get_actor_user_info(f'Singles_spect1_crystal')
singles_actor.output = paths.output / 'test038_ref_singles.root'

"""# motion of the spect, create also the run time interval
heads = [spect1]  # [spect1, spect2]

# create a list of run (total = 1 second)
n = 1
sim.run_timing_intervals = gam.range_timing(0, 1 * sec, n)

for head in heads:
    motion = sim.add_actor('MotionVolumeActor', f'Move_{head.name}')
    motion.mother = head.name
    motion.translations, motion.rotations = \
        gam.volume_orbiting_transform('x', 0, 180, n, head.translation, head.rotation)
    motion.priority = 5"""

phsp = sim.add_actor('PhaseSpaceActor', 'phsp')
phsp.mother = cyl.name
phsp.attributes = ['KineticEnergy', 'PrePosition',
                   'PreDirection', 'GlobalTime',
                   'EventPosition', 'TrackVertexMomentumDirection']
phsp.output = paths.output / 'test038_ref_phsp.root'

# go
sim.initialize()
sim.start()

# print stats
stats = sim.get_actor('Stats')
print(stats)

# check skipped particle (if AA)
s = 0
for source in sources.values():
    s += gam.get_source_skipped_particles(sim, source.name)
print(f'Skipped particles {s}')

# print nb hits
singles = uproot.open(singles_actor.output)['Singles_spect1_crystal']
print(f'Nb of singles : {singles.num_entries}')

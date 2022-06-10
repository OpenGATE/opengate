#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.phantom_nema_iec_body as gam_iec

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
ac = 100000 * BqmL
#ac = 10 * BqmL
ui.visu = False
if ui.visu:
    ac = 10 * BqmL  # per mL
    ui.number_of_threads = 1

# world size
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]
world.material = 'G4_AIR'

# iec phantom
iec_phantom = gam_iec.add_phantom(sim)

# cylinder for phsp
sph_surface = sim.add_volume('Sphere', 'phase_space_sphere')
sph_surface.rmin = 210 * mm
sph_surface.rmax = 211 * mm
sph_surface.color = [0, 1, 0, 1]
sph_surface.material = 'G4_AIR'

# physic list
p = sim.get_physics_user_info()
p.physics_list_name = 'G4EmStandardPhysics_option4'
sim.set_cut('world', 'all', 1 * mm)

# source sphere
gam_iec.add_spheres_sources(sim, 'iec', 'source1',
                            [10, 13, 17, 22, 28, 37],
                            [ac, ac, ac, ac, ac, ac], verbose=True)

sources = sim.source_manager.user_info_sources
for source in sources.values():
    source.particle = 'gamma'
    source.energy.type = 'mono'
    source.energy.mono = 140.5 * keV

# background source 1:10 ratio with sphere
#bg = gam_iec.add_background_source(sim, 'iec', 'source_bg', ac / 10, verbose=True)
#bg.particle = 'gamma'
#bg.energy.type = 'mono'
#bg.energy.mono = 140.5 * keV

# add stat actor
stat = sim.add_actor('SimulationStatisticsActor', 'Stats')
stat.output = paths.output / 'test038_train_stats.txt'

# filter gamma only
f = sim.add_filter('ParticleFilter', 'f')
f.particle = 'gamma'

# phsp
phsp = sim.add_actor('PhaseSpaceActor', 'phase_space')
phsp.mother = 'phase_space_sphere'
# we use PrePosition because this is the first step in the volume
phsp.attributes = ['KineticEnergy',
                   'PrePosition', 'PreDirection',
                   'TimeFromBeginOfEvent',  # not needed only to test with ideal reconstruction
                   # needed for gan_flag
                   'EventID',
                   'TrackVertexKineticEnergy',
                   # for conditional :
                   'EventPosition',
                   'TrackVertexMomentumDirection'
                   ]
phsp.output = paths.output / 'test038_train.root'
phsp.phsp_gan_flag = True  # this option allow to store all events even if absorbed
phsp.filters.append(f)
print(phsp)
print(phsp.output)

# go
sim.initialize()
sim.start()

# print stats
stats = sim.get_actor('Stats')
print(stats)

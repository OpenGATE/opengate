#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import contrib.gam_iec_phantom as gam_iec

# global log level
gam.log.setLevel(gam.RUN)

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.multi_threading = False
ui.random_engine = 'MersenneTwister'
ui.random_seed = 'auto'
ui.check_volumes_overlap = True

# change world size
m = gam.g4_units('m')
cm = gam.g4_units('cm')
nm = gam.g4_units('nm')
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# phase-space surface
phsp = sim.add_volume('Sphere', 'phsp')
phsp.material = world.material
phsp.Rmax = 30 * cm
phsp.Rmin = phsp.Rmax - 1 * nm
phsp.color = [1, 0, 0, 1]

# add a iec phantom
iec_phantom = gam_iec.add_phantom(sim)

# add all sphere sources
Bq = gam.g4_units('Bq')
kBq = gam.g4_units('Bq') * 1000
ac = 10 * kBq * 0.986  # if gamma, consider yield 98.6%
gam_iec.add_sources(sim, 'iec',  # [28], [ac])
                    [10, 13, 17, 22, 28, 37],
                    [ac, ac, ac, ac, ac, ac])

# modify the source type, set to Tc99m
sources = sim.source_manager.user_info_sources
MeV = gam.g4_units('MeV')
for source in sources.values():
    source.energy.type = 'mono'
    # source.particle = 'ion 43 99 143'  # Tc99m metastable: E = 143
    # source.energy.mono = 0
    source.particle = 'gamma'
    source.energy.mono = 0.1405 * MeV

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'stats')
stats.track_types_flag = True

# Hits tree Actor
ta = sim.add_actor('HitsActor', 'phase_space')
ta.attached_to = 'phsp'
ta.branches = ['KineticEnergy', 'PostPosition', 'PostDirection', 'Time']
ta.output = './output/spect_iec.root'

# FIXME
# f = sim.add_filter('particle')
# f.actor = 'phsp'
# f.particle = 'gamma'

# phys
mm = gam.g4_units('mm')
p = sim.get_physics_info()
p.physics_list_name = 'G4EmStandardPhysics_option4'
p.enable_decay = False  # not needed if gamma, needed if ion
cuts = p.production_cuts
cuts.world.gamma = 1 * mm
cuts.world.electron = 1 * mm
cuts.world.positron = 1 * mm

# run timing
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 1 * sec]]

# initialize & start
sim.initialize()
for source in sources.values():
    print(source)

# sim.apply_g4_command("/tracking/verbose 1")

sim.start()

# print results at the end
stats = sim.get_actor('stats')
print(stats)

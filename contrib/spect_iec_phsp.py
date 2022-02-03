#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_iec_phantom as gam_iec

# global log level

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = 'MersenneTwister'
ui.random_seed = 'auto'
ui.number_of_threads = 6

# change world size
m = gam.g4_units('m')
cm = gam.g4_units('cm')
nm = gam.g4_units('nm')
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# phase-space surface
phsp = sim.add_volume('Sphere', 'phsp')
phsp.material = world.material
phsp.rmax = 30 * cm
phsp.rmin = phsp.rmax - 1 * nm
phsp.color = [1, 1, 0, 1]

# add a iec phantom
iec_phantom = gam_iec.add_phantom(sim)

# add all sphere sources
Bq = gam.g4_units('Bq')
kBq = gam.g4_units('Bq') * 1000
gamma_yield = 0.986  # if gamma, consider yield 98.6%
ac = 50 * kBq * gamma_yield
ac = 1e5 * Bq
gam_iec.add_spheres_sources(sim, 'iec',  # [28], [ac])
                            [10, 13, 17, 22, 28, 37],
                            [ac, ac, ac, ac, ac, ac])

# Background source
'''bg1 = sim.add_source('Generic', 'bg1')
bg1.mother = f'{name}_center_cylinder_hole'
v = sim.get_volume_user_info(bg1.mother)
s = sim.get_solid_info(v)
bg_volume = s.cubic_volume / cm3
print(f'Volume of {bg1.mother} {bg_volume} cm3')
bg1.position.type = 'box'
bg1.position.size = gam.get_max_size_from_volume(sim, bg1.mother)
bg1.position.confine = bg1.mother
bg1.particle = p
bg1.energy.type = 'F18'
w = 1
bg1.activity = ac * bg_volume / 3 / w  # ratio with spheres
bg1.weight = w

# background source
# (I checked that source if confine only on mother, not including daughter volumes)
bg2 = sim.add_source('Generic', 'bg2')
bg2.mother = f'{name}_interior'
v = sim.get_volume_user_info(bg2.mother)
s = sim.get_solid_info(v)
bg_volume = s.cubic_volume / cm3
print(f'Volume of {bg2.mother} {bg_volume} cm3')
bg2.position.type = 'box'
bg2.position.size = gam.get_max_size_from_volume(sim, bg2.mother)
bg2.position.confine = bg2.mother
bg2.particle = p
bg2.energy.type = 'F18'
w = 20
bg2.activity = ac * bg_volume / 10 / w  # ratio with spheres
bg2.weight = w'''



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
ta = sim.add_actor('PhaseSpaceActor', 'phase_space')
ta.mother = 'phsp'
ta.branches = ['KineticEnergy', 'PostPosition', 'PostDirection', 'TimeFromBeginOfEvent']
ta.output = './output/spect_iec.root'

# FIXME
# f = sim.add_filter('particle')
# f.actor = 'phsp'
# f.particle = 'gamma'

# phys
mm = gam.g4_units('mm')
p = sim.get_physics_user_info()
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
stats.write('output/stats.txt')

# save

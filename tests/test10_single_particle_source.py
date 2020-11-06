#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam

gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(False)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456)

# set the world size like in the Gate macro
m = gam.g4_units('m')
world = sim.get_volume_info('World')
world.size = [2 * m, 2 * m, 2 * m]

# add a simple volume
waterbox = sim.add_volume('Box', 'waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
waterbox.material = 'G4_WATER'

# useful units
MeV = gam.g4_units('MeV')
keV = gam.g4_units('keV')
Bq = gam.g4_units('Bq')
deg = gam.g4_units('deg')
mm = gam.g4_units('mm')

# test sources
source = sim.add_source('SingleParticleSource', 'source1')
source.particle = 'gamma'
source.activity = 100000 * Bq
source.energy.mono_energy = 1 * MeV
p = source.position
p.pos_type = 'Volume'
p.shape = 'Sphere'
p.radius = 5 * mm
p.center = [-3 * cm, 30 * cm, -3 * cm]
d = source.direction
d.ang_dist_type = 'iso'
d.min_theta = 88 * deg
d.max_theta = 92 * deg
d.min_phi = 80 * deg
d.max_phi = 100 * deg

source = sim.add_source('SingleParticleSource', 'source2')
source.particle = 'proton'
source.activity = 1000 * Bq
p = source.position
p.pos_type = 'Beam'
p.shape = 'Circle'
p.center = [6 * cm, 5 * cm, -30 * cm]
p.beam_sigma_in_x = 2 * mm
p.beam_sigma_in_y = 2 * mm
e = source.energy
e.mono_energy = 140 * MeV
e.energy_dist_type = 'Gauss'
e.beam_sigma_in_e = 10 * MeV
source.direction.momentum_direction = [0, 0, 1]

# BUG
# source = sim.add_source('SingleParticleSource', 'source3')
# source.particle = 'gamma'
# source.activity = 10000 * Bq
# source.position.center = [9 * cm, -30 * cm, -3 * cm]
# source.position.pos_type = 'Volume'
# source.position.shape = 'Sphere'
# source.position.radius = 1 * cm
# source.direction.momentum_direction = [0, 1, 0]
# source.energy.energy_dist_type = 'Arb'
# source.energy.arb_energy_histo_file = 'data/energy_spectrum_In111.txt'
# source.energy.arb_interpolate = 'Lin'

# actors
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')

# src_info = sim.add_actor('SourceInfoActor', 'src_info')
# src_info.filename = 'output/sources.root'

dose = sim.add_actor('DoseActor', 'dose')
dose.save = 'output/test10-edep.mhd'
dose.attachedTo = 'waterbox'
dose.dimension = [50, 50, 50]
dose.spacing = [4 * mm, 4 * mm, 4 * mm]

# create G4 objects
sim.initialize()

# print after init
print(sim)
print('Simulation seed:', sim.seed)

# verbose
sim.g4_apply_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.RUN)
sim.start()

# get results
stats = sim.get_actor('Stats')
print(stats)

dose = sim.get_actor('dose')
print(dose)

# gate_test10
# Gate mac/main.mac
# Current version is two times slower :(
stats_ref = gam.read_stat_file('./gate_test10_generic_source/output/stat.txt')
print('-' * 80)
gam.assert_stats(stats, stats_ref, tolerance=0.02)
gam.assert_images('output/test10-edep.mhd', 'gate_test10_generic_source/output/output-Edep.mhd', tolerance=0.1)

gam.test_ok()

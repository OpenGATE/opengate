#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.number_of_threads = 1
gam.log.setLevel(gam.DEBUG)

# some units
cm = gam.g4_units('cm')
m = gam.g4_units('m')
deg = gam.g4_units('deg')

# set the world size like in the Gate macro
world = sim.world
world.size = [2 * m, 2 * m, 2 * m]

# add a simple volume
waterbox = sim.add_volume('Box', 'waterbox')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
waterbox.material = 'G4_WATER'

# volume where to confine
stuff = sim.add_volume('Cons', 'stuff')
stuff.mother = 'waterbox'
stuff.Rmin1 = 0
stuff.Rmax1 = 0.5 * cm
stuff.Rmin2 = 0
stuff.Rmax2 = 0.5 * cm
stuff.Dz = 2 * cm
stuff.DPhi = 360 * deg
stuff.translation = [-5 * cm, 0 * cm, 0 * cm]
stuff.material = 'G4_WATER'

# useful units
MeV = gam.g4_units('MeV')
keV = gam.g4_units('keV')
Bq = gam.g4_units('Bq')
deg = gam.g4_units('deg')
mm = gam.g4_units('mm')

# test confined source
source = sim.add_source('Generic', 'non_confined_src')
source.mother = 'stuff'
source.particle = 'gamma'
source.activity = 50000 * Bq / ui.number_of_threads
source.position.type = 'box'
source.position.size = [5 * cm, 5 * cm, 5 * cm]
source.direction.type = 'momentum'
source.direction.momentum = [-1, 0, 0]
source.energy.type = 'mono'
source.energy.mono = 1 * MeV

# test confined source
source = sim.add_source('Generic', 'confined_src')
source.mother = 'stuff'
source.particle = 'gamma'
source.activity = 50000 * Bq / ui.number_of_threads
source.position.type = 'box'
source.position.size = [5 * cm, 5 * cm, 5 * cm]  # should be larger than 'stuff'
source.position.translation = [1 * cm, 0, 0]
source.position.confine = 'stuff'
source.direction.type = 'momentum'
source.direction.momentum = [1, 0, 0]
source.energy.type = 'mono'
source.energy.mono = 1 * MeV

# actors
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')

dose = sim.add_actor('DoseActor', 'dose')
dose.save = 'output/test010-2-edep.mhd'
# dose.save = 'output_ref/test010-2-edep.mhd'
dose.mother = 'waterbox'
dose.dimension = [100, 100, 100]
dose.spacing = [4 * mm, 4 * mm, 4 * mm]

# create G4 objects
sim.initialize()

# print after init
print(sim)
print('Simulation seed:', sim.actual_random_seed)

# start simulation
gam.source_log.setLevel(gam.RUN)
sim.start()

# get results
stats = sim.get_actor('Stats')
print(stats)
# stats.write('output_ref/test010_confine_stats.txt')

# tests
stats_ref = gam.read_stat_file('output_ref/test010_confine_stats.txt')
is_ok = gam.assert_stats(stats, stats_ref, 0.10)
is_ok = is_ok and gam.assert_images('output/test010-2-edep.mhd',
                                    'output_ref/test010-2-edep.mhd',
                                    stats, tolerance=2)

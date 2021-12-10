#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import gam_g4 as g4
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
# units
m = gam.g4_units('m')
cm = gam.g4_units('cm')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
nm = gam.g4_units('nm')
mm = gam.g4_units('mm')

#  change world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# waterbox
waterbox = sim.add_volume('Box', 'waterbox')
waterbox.size = [10 * cm, 10 * cm, 10 * cm]
waterbox.material = 'G4_WATER'
waterbox.color = [0, 0, 1, 1]

# default source for tests
source = sim.add_source('Generic', 'mysource')
source.energy.mono = 50 * MeV
source.particle = 'proton'
source.position.type = 'sphere'
source.position.radius = 1 * cm
source.direction.type = 'iso'
source.activity = 10000 * Bq

# filter : keep gamma
f = sim.add_filter('ParticleFilter', 'f')
f.particle = 'gamma'
fp = sim.add_filter('ParticleFilter', 'fp')
fp.particle = 'e-'

# add dose actor
dose = sim.add_actor('DoseActor', 'dose')
dose.save = pathFile / '..' / 'output' / 'test023-edep.mhd'
# dose.save = 'output_ref/test023-edep.mhd'
dose.mother = 'waterbox'
dose.dimension = [100, 100, 100]
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.filters.append(fp)

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'Stats')
s.track_types_flag = True
s.filters.append(f)

print(s)
print(dose)
print('Filters: ', sim.filter_manager)
print(sim.filter_manager.dump())

# change physics
p = sim.get_physics_user_info()
p.physics_list_name = 'QGSP_BERT_EMZ'
cuts = p.production_cuts
cuts.world.gamma = 0.1 * mm
cuts.world.proton = 0.1 * mm
cuts.world.electron = 0.1 * mm
cuts.world.positron = 0.1 * mm

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# print results at the end
stat = sim.get_actor('Stats')
print(stat)
# stat.write('output_ref/test023_stats.txt')

# tests
stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'output_ref' / 'test023_stats.txt')
is_ok = gam.assert_stats(stat, stats_ref, 0.8)
is_ok = is_ok and gam.assert_images(pathFile / '..' / 'output' / 'test023-edep.mhd',
                                    pathFile / '..' / 'data' / 'output_ref' / 'test023-edep.mhd',
                                    stat, tolerance=48)

gam.test_ok(is_ok)

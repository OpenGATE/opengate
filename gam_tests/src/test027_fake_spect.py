#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import uproot
import matplotlib.pyplot as plt

paths = gam.get_common_test_paths(__file__, 'gate_test027_fake_spect')

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = 2

# units
m = gam.g4_units('m')
cm = gam.g4_units('cm')
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')

# world size
world = sim.world
world.size = [2 * m, 2 * m, 2 * m]

# material
sim.add_material_database(paths.data / 'GateMaterials.db')

# fake spect head
waterbox = sim.add_volume('Box', 'SPECThead')
waterbox.size = [55 * cm, 42 * cm, 18 * cm]
waterbox.material = 'G4_AIR'

# crystal
crystal = sim.add_volume('Box', 'crystal')
crystal.mother = 'SPECThead'
crystal.size = [55 * cm, 42 * cm, 2 * cm]
crystal.translation = [0, 0, 4 * cm]
crystal.material = 'NaITl'
crystal.color = [1, 1, 0, 1]

# colli
"""colli = sim.add_volume('Box', 'colli')
colli.mother = 'SPECThead'
colli.size = [55 * cm, 42 * cm, 6 * cm]
colli.material = 'Lead'
hole = sim.add_volume('Polyhedra', 'hole')
hole.mother = 'colli'
h = 5.8 * cm
hole.zplane = [-h / 2, h - h / 2]
hole.radius_outer = [0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm]
hole.translation = None
hole.rotation = None

size = [77, 100, 1]
#size = [7, 10, 1] #FIXME
tr = [7.01481 * mm, 4.05 * mm, 0]
## FIXME FIXME not correct position
start = [-(size[0] * tr[0]) / 2.0, -(size[1] * tr[1]) / 2.0, 0]
r1 = gam.repeat_array('colli1', start, size, tr)
start[0] += 3.50704 * mm
start[1] += 2.025 * mm
r2 = gam.repeat_array('colli2', start, size, tr)
hole.repeat = r1 + r2"""

# physic list
p = sim.get_physics_user_info()
p.physics_list_name = 'G4EmStandardPhysics_option4'
p.enable_decay = False
cuts = p.production_cuts
cuts.world.gamma = 0.01 * mm
cuts.world.electron = 0.01 * mm
cuts.world.positron = 1 * mm
cuts.world.proton = 1 * mm

# default source for tests
source = sim.add_source('Generic', 'Default')
source.particle = 'gamma'
source.energy.mono = 140.5 * keV
source.position.type = 'sphere'
source.position.radius = 4 * cm
source.position.translation = [0, 0, -15 * cm]
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.activity = 5000 * Bq / ui.number_of_threads

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# hits collection
hc = sim.add_actor('HitsCollectionActor', 'Hits')
hc.mother = crystal.name
hc.output = paths.output / 'test027.root'
hc.attributes = ['KineticEnergy', 'PostPosition', 'PrePosition',
                 'TotalEnergyDeposit', 'GlobalTime',
                 'VolumeName', 'TrackID',
                 'VolumeCopyNo', 'VolumeInstanceID']

# singles collection
sc = sim.add_actor('HitsAdderActor', 'Singles')
sc.mother = crystal.name
sc.input_hits_collection = 'Hits'
sc.policy = 'TakeEnergyWinner'
# sc.policy = 'TakeEnergyCentroid'
# same filename, there will be two branches in the file
sc.output = hc.output

sec = gam.g4_units('second')
ui.running_verbose_level = 2
sim.run_timing_intervals = [[0, 0.33 * sec], [0.33 * sec, 0.66 * sec], [0.66 * sec, 1 * sec]]

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# stat
gam.warning('Compare stats')
stats = sim.get_actor('Stats')
print(stats)
print(f'Number of runs was {stats.counts.run_count}. Set to 1 before comparison')
stats.counts.run_count = 1  # force to 1
stats_ref = gam.read_stat_file(paths.gate_output_ref / 'stat.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.07)

# root compare HITS
print()
gam.warning('Compare HITS')
gate_file = paths.gate_output_ref / 'spect.root'
checked_keys = ['posX', 'posY', 'posZ', 'edep', 'time', 'trackId']
gam.compare_root(gate_file, hc.output, "Hits", "Hits", checked_keys, paths.output / 'test027.png')

# Root compare SINGLES
print()
gam.warning('Compare SINGLES')
gate_file = paths.gate_output_ref / 'spect.root'
checked_keys = ['globalposX', 'globalposY', 'globalposZ', 'energy']
gam.compare_root(gate_file, sc.output, "Singles", "Singles", checked_keys, paths.output / 'test027_singles.png')

# this is the end, my friend
gam.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import uproot
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False

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
sim.add_material_database(pathFile / '..' / 'data' / 'GateMaterials.db')

# fake spect head
waterbox = sim.add_volume('Box', 'SPECThead')
waterbox.size = [55 * cm, 42 * cm, 18 * cm]
waterbox.material = 'G4_AIR'

# crystal
crystal = sim.add_volume('Box', 'crystal')
crystal.mother = 'SPECThead'
crystal.size = [0.5 * cm, 0.5 * cm, 2 * cm]
crystal.translation = None
crystal.rotation = None
crystal.material = 'NaITl'
## FIXME FIXME not correct position
start = [-25 * cm, -20 * cm, 4 * cm]
size = [100, 80, 1]
# size = [10, 8, 1] # FIXME
tr = [0.5 * cm, 0.5 * cm, 0]
crystal.repeat = gam.repeat_array('crystal', start, size, tr)
crystal.color = [1, 1, 0, 1]

# colli
"""colli = sim.add_volume('Box', 'colli')
colli.mother = 'SPECThead'
colli.size = [55 * cm, 42 * cm, 6 * cm]
colli.material = 'Lead'
hole = sim.add_volume('Polyhedra', 'hole')
hole.mother = 'colli'
h = 5.8 * cm
hole.zPlane = [-h / 2, h - h / 2]
hole.rOuter = [0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm]
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
source.activity = 5000 * Bq

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# hits collection
hc = sim.add_actor('HitsCollectionActor', 'hc')
hc.mother = crystal.name
hc.output = gam.check_filename_type(pathFile / '..' / 'output' / 'test027_hits.root')
hc.attributes = ['KineticEnergy', 'PostPosition', 'TotalEnergyDeposit', 'GlobalTime', 'VolumeName']

# create G4 objects
sim.initialize()

# start simulation
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 1 * sec]]
sim.start()

# stat
stats = sim.get_actor('Stats')
print(stats)
stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'gate' / 'gate_test027_fake_spect' / 'output' / 'stat.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.07)

# root
ref_hits = uproot.open(pathFile / '..' / 'data' / 'gate' / 'gate_test027_fake_spect' / 'output' / 'spect.root')['Hits']
rn = ref_hits.num_entries
ref_hits = ref_hits.arrays(library="numpy")
print(rn, ref_hits.keys())

hits = uproot.open(hc.output)['hc']
n = hits.num_entries
hits = hits.arrays(library="numpy")
print(n, hits.keys())

diff = gam.rel_diff(float(rn), n)
print(f'Nb values: {rn} {n} {diff:.2f}%')

# FIXME
keys1, keys2, scalings = gam.get_keys_correspondence(list(ref_hits.keys()))
scalings.append(1)
tols = [1.5] * len(keys1)
is_ok = gam.compare_trees(ref_hits, list(ref_hits.keys()),
                          hits, list(hits.keys()),
                          keys1, keys2, tols, scalings,
                          True) and is_ok

# this is the end, my friend
gam.test_ok(is_ok)

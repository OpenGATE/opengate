#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import uproot4 as uproot

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
gam.log.setLevel(gam.RUN)

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
sim.add_material_database('./data/GateMaterials.db')

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
#size = [10, 8, 1] # FIXME
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
source.activity = 2000 * Bq

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# hits collection
hc = sim.add_actor('HitsCollectionActor', 'hc')
hc.mother = crystal.name
hc.branches = ['KineticEnergy', 'PostPosition', 'DepositedEnergy', 'GlobalTime', 'VolumeName']
hc.branches = ['KineticEnergy', 'PostPosition']

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# stat
stats = sim.get_actor('Stats')
print(stats)
stats_ref = gam.read_stat_file('./gate_test024_spect_detector/output/stat.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.03)

# root
hits = uproot.open('hits.root')['Hits']
hits = hits.arrays(library="numpy")
n = hits.num_entries
print(n, hits)
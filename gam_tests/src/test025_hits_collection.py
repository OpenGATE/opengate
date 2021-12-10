#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import gam_g4
import uproot
import pathlib
import os
import matplotlib.pyplot as plt

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = 1  # FIXME

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
crystal1 = sim.add_volume('Box', 'crystal1')
crystal1.mother = 'SPECThead'
crystal1.size = [0.5 * cm, 0.5 * cm, 2 * cm]
crystal1.translation = None
crystal1.rotation = None
crystal1.material = 'NaITl'
start = [-25 * cm, -20 * cm, 4 * cm]
size = [100, 40, 1]
# size = [100, 80, 1]
tr = [0.5 * cm, 0.5 * cm, 0]
crystal1.repeat = gam.repeat_array('crystal1', start, size, tr)
crystal1.color = [1, 1, 0, 1]

# additional volume
crystal2 = sim.add_volume('Box', 'crystal2')
crystal2.mother = 'SPECThead'
crystal2.size = [0.5 * cm, 0.5 * cm, 2 * cm]
crystal2.translation = None
crystal2.rotation = None
crystal2.material = 'NaITl'
start = [-25 * cm, 0 * cm, 4 * cm]
size = [100, 40, 1]
tr = [0.5 * cm, 0.5 * cm, 0]
crystal2.repeat = gam.repeat_array('crystal2', start, size, tr)
crystal2.color = [0, 1, 0, 1]

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
hc = sim.add_actor('HitsCollectionActor', 'hc')
# hc.mother = [crystal1.name, crystal2.name]  # FIXME
hc.mother = [crystal1.name, crystal2.name]
hc.output = pathFile / '..' / 'output' / 'test0025_hits.root'
hc.branches = ['KineticEnergy', 'PostPosition', 'TotalEnergyDeposit', 'GlobalTime', 'VolumeName']


# dynamic branch creation (SLOW !)
def branch_fill(branch, step, touchable):
    e = step.GetTotalEnergyDeposit()
    branch.push_back_double(e)
    # branch.push_back_double(123.3)
    # print('done')


# FIXME bug at destructor
gam_g4.GamBranch.DefineBranch('MyBranch', 'D', branch_fill)
hc.branches.append('MyBranch')
print('List of active branches (including dynamic branch)', hc.branches)

# create G4 objects
sim.initialize()

# start simulation
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 1 * sec]]
sim.start()

# stat
stats = sim.get_actor('Stats')
print(stats)
stats_ref = gam.read_stat_file(
    pathFile / '..' / 'data' / 'gate' / 'gate_test025_hits_collection' / 'output' / 'stat.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.06)

# read Gate root file
gate_file = pathFile / '..' / 'data' / 'gate' / 'gate_test025_hits_collection' / 'output' / 'hits.root'
ref_hits = uproot.open(gate_file)['Hits']
print(gate_file)
rn = ref_hits.num_entries
ref_hits = ref_hits.arrays(library="numpy")
print(f'Reference tree: {gate_file} n={rn} {ref_hits.keys()}')

# read this simulation output root file
hits = uproot.open(hc.output)['Hits']
n = hits.num_entries
hits = hits.arrays(library="numpy")
print(f'Current tree : {hc.output} n={n} {hits.keys()}')

# compare number of values in both root files
diff = gam.rel_diff(float(rn), n)
is_ok = gam.print_test(diff < 6, f'Nb values: {rn} {n} {diff:.2f}%') and is_ok

# print branches
hc = sim.get_actor('hc')
ab = gam_g4.GamBranch.GetAvailableBranches()
bn = [b.fBranchName for b in ab]
print(f'Available branches {bn}')
tree = hc.GetHits()
bn = [b.fBranchName for b in tree.fBranches]
print(f'Active branches {bn}')

# Compare branch in memory
# edep = tree.GetBranch('TotalEnergyDeposit')
# print('edep branch', edep)
# print(edep.size())


# compare some hits with gate
keys1, keys2, scalings = gam.get_keys_correspondence(list(ref_hits.keys()))
keys1.append('edep')
keys2.append('MyBranch')
scalings.append(1)
tols = [1.0] * len(keys1)  # FIXME
is_ok = gam.compare_trees(ref_hits, list(ref_hits.keys()),
                          hits, list(hits.keys()),
                          keys1, keys2, tols, scalings,
                          True) and is_ok

# figure
plt.suptitle(f'Values: {rn} vs {n}')
# plt.show()
fn = pathFile / '..' / 'output' / 'test025.png'
plt.savefig(fn)
print(f'Figure in {fn}')

# BOTH are needed for the moment
tree.FreeBranches()
gam_g4.GamBranch.FreeAvailableBranches()

# this is the end, my friend
gam.test_ok(is_ok)

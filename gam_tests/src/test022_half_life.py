#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# import pdb
import gam_gate as gam
import uproot
import sys
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gam.Simulation()

# multithread ?
argv = sys.argv
n = 1
if len(argv) > 1:
    n = int(argv[1])

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = n
print(ui)

# units
m = gam.g4_units('m')
cm = gam.g4_units('cm')
mm = gam.g4_units('mm')
nm = gam.g4_units('nm')
keV = gam.g4_units('keV')
Bq = gam.g4_units('Bq')
sec = gam.g4_units('s')

# set the world size like in the Gate macro
world = sim.world
world.size = [1 * m, 1 * m, 2 * m]

# waterbox (not really used here)
waterbox = sim.add_volume('Box', 'waterbox')
waterbox.size = [10 * cm, 10 * cm, 10 * cm]
waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
waterbox.material = 'G4_AIR'

# detector
detector = sim.add_volume('Box', 'detector')
detector.size = [80 * cm, 80 * cm, 1 * nm]
detector.translation = [0, 0, 30 * cm]
detector.material = 'G4_BGO'
detector.color = [1, 0, 0, 1]

# physics
p = sim.get_physics_user_info()
p.physics_list_name = 'QGSP_BERT_EMZ'
p.enable_decay = True
cuts = p.production_cuts
cuts.world.gamma = 1 * mm
cuts.world.proton = 1 * mm
cuts.world.electron = 1 * mm
cuts.world.positron = 1 * mm

# source #1
source1 = sim.add_source('Generic', 'source1')
source1.particle = 'gamma'
source1.energy.mono = 100 * keV
source1.position.type = 'disc'
source1.position.radius = 2 * cm
source1.position.translation = [0, 0, -10 * cm]
source1.direction.type = 'focused'
source1.direction.focus_point = [0, 0, 0]
source1.activity = 10000 * Bq / ui.number_of_threads
source1.half_life = 2 * sec

# source #2
source2 = sim.add_source('Generic', 'source2')
source2.particle = 'gamma'
source2.energy.mono = 200 * keV
source2.position.type = 'disc'
source2.position.radius = 2 * cm
source2.position.translation = [0, 0, -10 * cm]
source2.direction.type = 'focused'
source2.direction.focus_point = [0, 0, 0]
source2.activity = 10000 * Bq / ui.number_of_threads
# source2.n = 50

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')
stats.track_types_flag = True

# hit actor
ta = sim.add_actor('PhaseSpaceActor', 'PhaseSpace')
ta.mother = 'detector'
ta.attributes = ['KineticEnergy', 'GlobalTime']
ta.output = pathFile / '..' / 'output' / 'test022_half_life.root'

# timing
sim.run_timing_intervals = [[1 * sec, 10 * sec],
                            [15 * sec, 20 * sec]]  # "hole" in the timeline

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# get result
stats = sim.get_actor('Stats')
print(stats)

# read phsp

root = uproot.open(ta.output)
branch = root['PhaseSpace']['GlobalTime']
time = branch.array(library='numpy') / sec
branch = root['PhaseSpace']['KineticEnergy']
E = branch.array(library='numpy')

# consider time of arrival for both sources
time1 = time[E < 110 * keV]
time2 = time[E > 110 * keV]

# fit for half life
start_time = sim.run_timing_intervals[0][0] / sec
end_time = sim.run_timing_intervals[0][1] / sec
hl, xx, yy = gam.fit_exponential_decay(time1, start_time, end_time)
# compare with source half_life (convert in sec)
tol = 0.05
hl_ref = source1.half_life / sec
diff = abs(hl - hl_ref) / hl_ref
is_ok = b = diff < tol
diff *= 100
gam.print_test(b, f'Half life {hl_ref:.2f} sec vs {hl:.2f} sec : {diff:.2f}% ')

# check second source
m = len(time2)
start_time2 = sim.run_timing_intervals[1][0] / sec
end_time2 = sim.run_timing_intervals[1][1] / sec
# number of elements is around activity times the duration (per thread)
m_ref = source2.activity / Bq * (end_time - start_time + end_time2 - start_time2) * ui.number_of_threads
diff = abs(m - m_ref) / m_ref
b = diff < tol
diff *= 100
gam.print_test(b, f'Events for source #2:  {m_ref} vs {m} -> {diff:.2f}% ')
is_ok = is_ok and b

# check thread
b = (ui.number_of_threads * len(sim.run_timing_intervals) == stats.counts.run_count)
gam.print_test(b, f'Number of run: {stats.counts.run_count}')

is_ok = is_ok and b

gam.test_ok(is_ok)

# plot debug
"""
fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(5, 5))
a = ax
a.hist(time1, bins=100, label='decay source', histtype='stepfilled', alpha=0.5, density=True)
a.hist(time2, bins=100, label='constant source', histtype='stepfilled', alpha=0.5, density=True)
a.plot(xx, yy, label='fit half-life {:.2f} sec'.format(hl))
a.legend()
a.set_xlabel('time (s)')
a.set_ylabel('detected photon')
plt.show()
"""

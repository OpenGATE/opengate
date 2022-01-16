#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_ge_nm670_spect as gam_spect

paths = gam.get_common_test_paths(__file__, 'gate_test028_ge_nm670_spect')

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = True
ui.visu = True
ui.number_of_threads = 1
ui.check_volumes_overlap = False

# units
m = gam.g4_units('m')
cm = gam.g4_units('cm')
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')

# world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]
world.material = 'G4_AIR'

# spect head
spect = gam_spect.add_spect(sim, 'spect')
spect.translation = [0, 0, -20 * cm]

# waterbox
waterbox = sim.add_volume('Box', 'waterbox')
waterbox.size = [15 * cm, 15 * cm, 15 * cm]
waterbox.material = 'G4_WATER'

# physic list
p = sim.get_physics_user_info()
p.physics_list_name = 'G4EmStandardPhysics_option4'
p.enable_decay = False
cuts = p.production_cuts
cuts.world.gamma = 10 * mm
cuts.world.electron = 10 * mm
cuts.world.positron = 10 * mm
cuts.world.proton = 10 * mm

"""cuts.spect.gamma = 0.1 * mm
cuts.spect.electron = 0.1 * mm
cuts.spect.positron = 0.1 * mm"""

# default source for tests
activity = 3 * Bq
beam1 = sim.add_source('Generic', 'beam1')
beam1.mother = waterbox.name
beam1.particle = 'gamma'
beam1.energy.mono = 140.5 * keV
beam1.position.type = 'sphere'
beam1.position.radius = 3 * cm
beam1.position.translation = [0, 0, 0 * cm]
beam1.direction.type = 'iso'
beam1.activity = activity / ui.number_of_threads

beam2 = sim.add_source('Generic', 'beam2')
beam2.mother = waterbox.name
beam2.particle = 'gamma'
beam2.energy.mono = 140.5 * keV
beam2.position.type = 'sphere'
beam2.position.radius = 3 * cm
beam2.position.translation = [18, 0, 0 * cm]
beam2.direction.type = 'iso'
beam2.activity = activity / ui.number_of_threads

beam3 = sim.add_source('Generic', 'beam3')
beam3.mother = waterbox.name
beam3.particle = 'gamma'
beam3.energy.mono = 140.5 * keV
beam3.position.type = 'sphere'
beam3.position.radius = 1 * cm
beam3.position.translation = [0, 10, 0 * cm]
beam3.direction.type = 'iso'
beam3.activity = activity / ui.number_of_threads

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# hits collection
"""hc = sim.add_actor('HitsCollectionActor', 'Hits')
hc.mother = crystal.name
hc.output = paths.output / 'test028.root'
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
sc.output = hc.output"""

sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 1 * sec]]

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

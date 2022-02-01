#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_ge_nm670_spect as gam_spect
from scipy.spatial.transform import Rotation
import numpy as np

paths = gam.get_common_test_paths(__file__, 'gate_test028_ge_nm670_spect')

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = 1
ui.check_volumes_overlap = False

# units
m = gam.g4_units('m')
cm = gam.g4_units('cm')
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')
kBq = 1000 * Bq

# world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]
world.material = 'G4_AIR'

# spect head (debug mode = very small collimator)
spect = gam_spect.add_spect(sim, 'spect', collimator=False, debug=False)
psd = 6.11 * cm
p = [0, 0, -(20 * cm + psd)]
spect.translation, spect.rotation = gam.get_transform_orbiting(p, 'y', -15)
print(spect.translation, spect.rotation)

# waterbox
waterbox = sim.add_volume('Box', 'waterbox')
waterbox.size = [15 * cm, 15 * cm, 15 * cm]
waterbox.material = 'G4_WATER'
blue = [0, 1, 1, 1]
waterbox.color = blue

# physic list
p = sim.get_physics_user_info()
p.physics_list_name = 'G4EmStandardPhysics_option4'
p.enable_decay = False
cuts = p.production_cuts
cuts.world.gamma = 10 * mm
cuts.world.electron = 10 * mm
cuts.world.positron = 10 * mm
cuts.world.proton = 10 * mm

cuts.spect.gamma = 0.1 * mm
cuts.spect.electron = 0.01 * mm
cuts.spect.positron = 0.1 * mm

# default source for tests
activity = 30 * kBq
beam1 = sim.add_source('Generic', 'beam1')
beam1.mother = waterbox.name
beam1.particle = 'gamma'
beam1.energy.mono = 140.5 * keV
beam1.position.type = 'sphere'
beam1.position.radius = 3 * cm
beam1.position.translation = [0, 0, 0 * cm]
beam1.direction.type = 'momentum'
beam1.direction.momentum = [0, 0, -1]
# beam1.direction.type = 'iso'
beam1.activity = activity / ui.number_of_threads

beam2 = sim.add_source('Generic', 'beam2')
beam2.mother = waterbox.name
beam2.particle = 'gamma'
beam2.energy.mono = 140.5 * keV
beam2.position.type = 'sphere'
beam2.position.radius = 3 * cm
beam2.position.translation = [18 * cm, 0, 0]
beam2.direction.type = 'momentum'
beam2.direction.momentum = [0, 0, -1]
# beam2.direction.type = 'iso'
beam2.activity = activity / ui.number_of_threads

beam3 = sim.add_source('Generic', 'beam3')
beam3.mother = waterbox.name
beam3.particle = 'gamma'
beam3.energy.mono = 140.5 * keV
beam3.position.type = 'sphere'
beam3.position.radius = 1 * cm
beam3.position.translation = [0, 10 * cm, 0]
beam3.direction.type = 'momentum'
beam3.direction.momentum = [0, 0, -1]
# beam3.direction.type = 'iso'
beam3.activity = activity / ui.number_of_threads

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# hits collection
hc = sim.add_actor('HitsCollectionActor', 'Hits')
# get crystal volume by looking for the word crystal in the name
l = sim.get_all_volumes_user_info()
crystal = l[[k for k in l if 'crystal' in k][0]]
hc.mother = crystal.name
print(crystal.name)
print('Crystal : ', crystal.name)
hc.output = paths.output / 'test028.root'
print('output', hc.output)
hc.attributes = ['PostPosition', 'TotalEnergyDeposit',
                 'GlobalTime', 'KineticEnergy', 'ProcessDefinedStep']

# singles collection
sc = sim.add_actor('HitsAdderActor', 'Singles')
sc.mother = crystal.name
sc.input_hits_collection = 'Hits'
sc.policy = 'TakeEnergyWinner'
# sc.policy = 'TakeEnergyCentroid'
sc.skip_attributes = ['KineticEnergy', 'ProcessDefinedStep', 'KineticEnergy']
sc.output = hc.output

# EnergyWindows
cc = sim.add_actor('HitsEnergyWindowsActor', 'EnergyWindows')
cc.mother = crystal.name
cc.input_hits_collection = 'Singles'
cc.channels = [{'name': 'scatter', 'min': 114 * keV, 'max': 126 * keV},
               {'name': 'peak140', 'min': 126 * keV, 'max': 154.55 * keV},
               {'name': 'spectrum', 'min': 0 * keV, 'max': 5000 * keV}  # should be strictly equal to 'Singles'
               ]
cc.output = hc.output

# 2D binning projection
proj = sim.add_actor('HitsProjectionActor', 'Projection')
proj.mother = crystal.name
proj.input_hits_collections = 'peak140'  # ['scatter', 'peak140', 'spectrum'] # FIXME
proj.spacing = [4.41806 * mm, 4.41806 * mm, 100 * mm]
proj.dimension = [128, 128, 1]
# proj.plane = 'XY'
proj.output = paths.output / 'proj028.mhd'

sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1 * sec]]

# create G4 objects
sim.initialize()
# sim.apply_g4_command('/tracking/verbose 1')

# start simulation
sim.start()

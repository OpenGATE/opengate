#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import gam_g4 as g4

# global log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()

# verbose and GUI
sim.set_g4_verbose(True)
sim.set_g4_visualisation_flag(False)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456)

# add a material database
sim.add_material_database('GateMaterials.db')

#  change world size
m = gam.g4_units('m')
sim.volumes_info.World.size = [1 * m, 1 * m, 1 * m]

# add a simple volume
fake = sim.add_volume('Box', 'fake')
cm = gam.g4_units('cm')
fake.size = [30 * cm, 30 * cm, 30 * cm]
fake.translation = [0 * cm, 0 * cm, 0 * cm]
fake.material = 'G4_AIR'
fake.color = [0, 0, 1, 1]  # blue

# waterbox
patient = sim.add_volume('Box', 'patient')
patient.mother = 'fake'
patient.size = [20 * cm, 20 * cm, 20 * cm]
patient.translation = [0 * cm, 0 * cm, 0 * cm]
patient.material = 'G4_WATER'
patient.color = [0, 0, 1, 1]  # blue

# voxel volume
#patient = sim.add_volume('Image', 'patient')
patient.image = 'patient-4mm.mhd'
patient.mother = 'fake'
mm = gam.g4_units('mm')
patient.size = [252 * mm, 252 * mm, 220 * mm]  # FIXME auto from img
patient.spacing = [4 * mm, 4 * mm, 4 * mm]  # FIXME auto from img
patient.dimension = [63, 63, 55]  # FIXME auto from img

# patient.pixel_values_to_material = PixelValueToMaterial('val2mat.txt')

# default source for tests
source = sim.add_source('TestProtonTime', 'Default')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
source.energy = 150 * MeV
nm = gam.g4_units('nm')
source.radius = 1 * nm
source.activity = 300 * Bq

# add dose actor
dose = sim.add_actor('Dose3', 'dose')
dose.save = 'dose_toto.mhd'
dose.attachedTo = 'patient'
dose.dimension = [99, 99, 99]
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.translation

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')

# run timing 
sec = gam.g4_units('second')
# sim.run_timing_intervals = [[0, 1 * sec]]

print(f'Source types: {sim.dump_source_types()}')
print(sim.dump_sources())
print(sim.dump_volumes())

# create G4 objects
sim.initialize()

# explicit check overlap (already performed during initialize)
sim.check_geometry_overlaps(verbose=True)

# print info
print(sim.dump_volumes())

# verbose
sim.g4_apply_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.RUN)
sim.start()

# print results at the end
stat = sim.actors_info.Stats.g4_actor
print(stat)

d = sim.actors_info.dose.g4_actor
print('dose', d)
d.SaveImage()

# WB
# NumberOfEvents = 101
# NumberOfTracks = 11897
# NumberOfSteps  = 26690
# NumberOfGeometricalSteps  = 233
# NumberOfPhysicalSteps     = 26457

# Vox
# NumberOfEvents = 101
# NumberOfTracks = 13751
# NumberOfSteps  = 34225
# NumberOfGeometricalSteps  = 3884
# NumberOfPhysicalSteps     = 30341

# gam.test_ok()

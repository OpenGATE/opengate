#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import platform
from scipy.spatial.transform import Rotation

# global log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()

# verbose and GUI
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(False)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456)

# add a material database
sim.add_material_database('data/GateMaterials.db')

#  change world size
m = gam.g4_units('m')
sim.volumes_info.World.size = [1 * m, 1 * m, 1 * m]

# add a simple fake volume to test hierarchy
# translation and rotation like in the Gate macro
fake = sim.add_volume('Box', 'fake')
cm = gam.g4_units('cm')
fake.size = [40 * cm, 40 * cm, 40 * cm]
fake.material = 'G4_AIR'
fake.color = [1, 0, 1, 1]

# image
patient = sim.add_volume('Image', 'patient')
patient.image = 'data/patient-4mm.mhd'
patient.mother = 'fake'

# default source for tests
source = sim.add_source('TestProtonTime', 'mysource')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
source.energy = 130 * MeV
mm = gam.g4_units('mm')
source.radius = 10 * mm
source.activity = 3000 * Bq
source.translation = [0, 0, -14 * cm]

# add dose actor
dose = sim.add_actor('DoseActor', 'dose')
dose.save = 'output/test9-edep.mhd'
dose.attachedTo = 'patient'
dose.dimension = [99, 99, 99]
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.img_coord_system = True  # default is True
dose.translation = [2 * mm, 3 * mm, -2 * mm]

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'Stats')

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
print(d)

# tests
gam.assert_stats(stat, './gate_test9_voxels/output/stat.txt', 0.1)
gam.assert_images('output/test9-edep.mhd', 'gate_test9_voxels/output/output-Edep.mhd', tolerance=0.1)

gam.test_ok()

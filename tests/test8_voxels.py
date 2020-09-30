#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import gam_g4 as g4

# global log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()

# verbose and GUI
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(True)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 123456)

# add a material database
sim.add_material_database('GateMaterials.db')

#  change world size
m = gam.g4_units('m')
sim.volumes_info.World.size = [1.5 * m, 1.5 * m, 1.5 * m]

# add a simple volume
waterbox = sim.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [6 * cm, 6 * cm, 6 * cm]
waterbox.translation = [0 * cm, 0 * cm, 35 * cm]
waterbox.material = 'G4_WATER'
waterbox.color = [0, 0, 1, 1]  # blue

# voxel volume
patient = sim.add_volume('Image', 'patient')
patient.image = 'patient-4mm.mhd'
mm = gam.g4_units('mm')
patient.size = [252 * mm, 252 * mm, 220 * mm]  # FIXME auto from img
patient.pixel_size = [4 * mm, 4 * mm, 4 * mm]  # FIXME auto from img
patient.image_size = [63, 63, 55]
# patient.pixel_values_to_material = PixelValueToMaterial('val2mat.txt')

# default source for tests
source = sim.add_source('TestProtonTime', 'Default')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
source.energy = 240 * MeV
source.diameter = 2 * cm
source.activity = 50 * Bq

# add stat actor
stats = sim.add_actor('SimulationStatistics', 'Stats')

# run timing 
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 0.5 * sec]
                            # ,[0.5 * sec, 1.2 * sec]
                            ]

print(f'Source types: {sim.dump_source_types()}')
print(sim.dump_sources())
print(sim.dump_volumes())

# create G4 objects
sim.initialize()

# explicit check overlap (already performed during initialize)
sim.check_geometry_overlaps(verbose=True)

# print info
print(sim.dump_volumes())

# print info material db
print('Material info:')
print('\t databases    :', sim.dump_material_database_names())
print('\t mat in NIST  :', sim.dump_material_database('NIST'))
print('\t mat in db    :', sim.dump_material_database('GateMaterials.db'))
print('\t defined mat  :', sim.dump_defined_material())

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

gam.test_ok()

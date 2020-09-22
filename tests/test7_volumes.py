#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import gam_g4 as g4
from scipy.spatial.transform import Rotation
import numpy as np

gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()

# verbose and GUI
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(True)

# set random engine
sim.set_random_engine("MersenneTwister", 123456)

#  change world size
m = gam.g4_units('m')
sim.volumes_info.World.size = [1 * m, 1 * m, 1 * m]

# add a simple volume
waterbox = sim.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'Water'

# another (child) volume with rotation
mm = gam.g4_units('mm')
sheet = sim.add_volume('Box', 'Sheet')
sheet.size = [30 * cm, 30 * cm, 1 * mm]
sheet.mother = 'Waterbox'
sheet.material = 'Aluminium'
r = Rotation.from_euler('x', 33, degrees=True)
center = [0 * cm, 0 * cm, 10 * cm]
t = gam.get_translation_from_rotation_with_center(r, center)
sheet.rotation = r.as_matrix()
sheet.translation = t + [0 * cm, 0 * cm, -10 * cm]

# A sphere
sph = sim.add_volume('Sphere', 'sph')
sph.Rmax = 3 * cm
# sph.toto = 12  # ignored
sph.mother = 'Waterbox'
sph.translation = [0 * cm, 0 * cm, 2 * cm]
sph.material = 'Aluminium'

# FIXME check geometry ?

# default source for tests
source = sim.add_source('TestProtonTime', 'Default')
MeV = gam.g4_units('MeV')
Bq = gam.g4_units('Bq')
source.energy = 190 * MeV
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
print(sim.dump_volumes(1))

# create G4 objects
sim.initialize()

# print info
print(sim.dump_sources())
print(sim.dump_volumes(1))

# verbose
sim.g4_apply_command('/tracking/verbose 0')
# sim.g4_com("/run/verbose 2")
# sim.g4_com("/event/verbose 2")
# sim.g4_com("/tracking/verbose 1")

# start simulation
gam.source_log.setLevel(gam.RUN)
sim.start()

# print results at the end
a = sim.actors_info.Stats.g4_actor
print(a)

gam.test_ok()

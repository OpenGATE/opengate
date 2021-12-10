#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_iec_phantom as gam_iec
from scipy.spatial.transform import Rotation
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# global log level
# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False

#  change world size
m = gam.g4_units('m')
cm = gam.g4_units('cm')
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# add a iec phantom
iec_phantom = gam_iec.add_phantom(sim)
iec_phantom.translation = [3 * cm, 1 * cm, 0 * cm]
iec_phantom.rotation = Rotation.from_euler('y', 33, degrees=True).as_matrix()

# simple source
# gam_iec.add_sources(sim, 'iec', 'all')
kBq = gam.g4_units('Bq') * 1000
ac = 2 * kBq
gam_iec.add_spheres_sources(sim, 'iec', 'iec_source',
                            [10, 13, 17, 22, 28, 37],
                            # [ac, 0, 0, 0, 0, 0])
                            [ac, ac, ac, ac, ac, ac])

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor', 'stats')
stats.track_types_flag = True

# add dose actor
dose = sim.add_actor('DoseActor', 'dose')
dose.save = pathFile / '..' / 'output' / 'test015.mhd'
# dose.save = 'output_ref/test015_ref.mhd'
dose.mother = 'iec'
dose.dimension = [100, 100, 100]
mm = gam.g4_units('mm')
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.translation = [0 * mm, 0 * mm, 0 * mm]

# run timing
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 1 * sec]]

print(sim.volume_manager.dump_tree())
print(sim.source_manager.dump())

# initialize & start
sim.initialize()
sim.start()

# Only for reference stats:
stats = sim.get_actor('stats')
# stats.write('output_ref/test015_stats.txt')

# check
stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'output_ref' / 'test015_stats.txt')
is_ok = gam.assert_stats(stats, stats_ref, 0.07)
is_ok = is_ok and gam.assert_images(pathFile / '..' / 'output' / 'test015.mhd',
                                    pathFile / '..' / 'data' / 'output_ref' / 'test015_ref.mhd',
                                    stats, tolerance=65)

gam.test_ok(is_ok)

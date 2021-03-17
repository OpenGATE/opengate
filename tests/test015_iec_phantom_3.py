#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import contrib.gam_iec as gam_iec
from scipy.spatial.transform import Rotation

# global log level
gam.log.setLevel(gam.DEBUG)

# create the simulation
sim = gam.Simulation()

# verbose and GUI
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(True)

# set random engine
sim.set_g4_random_engine("MersenneTwister", 12352316)

#  change world size
m = gam.g4_units('m')
cm = gam.g4_units('cm')
world = sim.get_volume_info('world')
world.size = [1 * m, 1 * m, 1 * m]

# add a iec phantom
iec_phantom = gam_iec.add_phantom(sim)
iec_phantom.translation = [5 * cm, 10 * cm, 0 * cm]
iec_phantom.rotation = Rotation.from_euler('y', 33, degrees=True).as_matrix()

# simple source
# gam_iec.add_sources(sim, 'iec', 'all')
gam_iec.add_sources(sim, 'iec',
                    [10, 13, 17, 22, 28, 37],
                    [100, 100, 100, 100, 100, 100])

# add stat actor
stats = sim.add_actor('SimulationStatisticsActor')
stats.track_types_flag = True
stats = stats.object  ## FIXME pas cool

# run timing
sec = gam.g4_units('second')
sim.run_timing_intervals = [[0, 0.01 * sec]]

print(sim.volume_manager.dump_tree())

print(sim.source_manager.dump(0))

# initialize & start
sim.initialize()
sim.start()

# print results at the end
print(stats)

# check
stats_ref = gam.read_stat_file('./stats_test015_iec_phantom_1.txt')
# the number of step is different, which is expected
stats_ref.SetStepCount(397972)
is_ok = gam.assert_stats(stats, stats_ref, 0.05)

gam.test_ok(is_ok)

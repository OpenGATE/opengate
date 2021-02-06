#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import gam_g4 as g4

# verbose level
gam.log.setLevel(gam.INFO)

# create the simulation
sim = gam.Simulation()

# main options
sim.set_g4_verbose(False)
sim.set_g4_visualisation_flag(False)
sim.set_g4_multi_thread(False)
sim.set_g4_random_engine("MersenneTwister", 12346)

# set the world size like in the Gate macro
m = gam.g4_units('m')
world = sim.get_volume_info('World')
world.size = [3 * m, 3 * m, 3 * m]

# add a simple waterbox volume
waterbox = sim.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'G4_WATER'

# physics
p = sim.physics_manager
p.name = 'QGSP_BERT_EMZ'
# p.name = 'G4EmLivermorePhysics'
# p.name = 'G4EmStandardPhysics_option4'
p.decay = True

em = p.g4_em_parameters
em.SetFluo(True)
em.SetAuger(True)
em.SetAugerCascade(True)
em.SetPixe(True)

# print info about physics
print(p)
print(p.g4_em_parameters.ToString())
print(p.dump_physics_list())

# default source for tests
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')

source = sim.add_source('Generic')
source.particle = 'gamma'
source.energy.mono = 80 * keV
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.activity = 100 * Bq

source = sim.add_source('Generic')
source.particle = 'ion 9 18'  # or F18 or Fluorine18
source.position.type = 'sphere'
source.position.center = [10 * mm, 10 * mm, 20 * mm]
source.position.radius = 3 * mm
source.direction.type = 'iso'
source.activity = 1000 * Bq

source = sim.add_source('Generic')
source.particle = 'ion 53 124'  # 53 124 0 0       # Iodine 124
source.position.type = 'sphere'
source.position.center = [-10 * mm, -10 * mm, -40 * mm]
source.position.radius = 1 * mm
source.direction.type = 'iso'
source.activity = 1000 * Bq

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# create G4 objects
sim.initialize()

# start simulation
# sim.set_g4_verbose(True)
# sim.apply_g4_command("/tracking/verbose 1")
gam.source_log.setLevel(gam.DEBUG)  # FIXME do not work
sim.start()

stats = sim.get_actor('Stats')

# gate_test4_simulation_stats_actor
# Gate mac/main.mac
# stats_ref = gam.read_stat_file('./gate_test13_phys_lists/output/stat.txt')
stats_ref = gam.SimulationStatisticsActor('test')
stats_ref.SetRunCount(1)
stats_ref.SetEventCount(2212)
stats_ref.SetTrackCount(112422)
stats_ref.SetStepCount(500277)
sec = gam.g4_units('second')
stats_ref.fDuration = stats_ref.GetEventCount() / 646.6 * sec
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.1)

gam.test_ok(is_ok)

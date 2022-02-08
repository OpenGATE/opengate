#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import pathlib
import gam_g4 as g4
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.running_verbose_level = 0
ui.visu = False
ui.number_of_threads = 5
# special debug mode : force MT even with one single thread
ui.force_multithread_mode = True
ui.random_engine = 'MixMaxRng'
ui.random_seed = 'auto'

"""
    Warning: we can only see the speed up of the MT mode for large nb of particles (>2e6)  
"""

# set the world size like in the Gate macro
m = gam.g4_units('m')
world = sim.world
world.size = [3 * m, 3 * m, 3 * m]
world.material = 'G4_AIR'

# add a simple waterbox volume
waterbox = sim.add_volume('Box', 'Waterbox')
cm = gam.g4_units('cm')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'G4_WATER'

# physic list
p = sim.get_physics_user_info()
p.physics_list_name = 'QGSP_BERT_EMV'
cuts = p.production_cuts
um = gam.g4_units('um')
cuts.world.gamma = 700 * um
cuts.world.electron = 700 * um
cuts.world.positron = 700 * um
cuts.world.proton = 700 * um

# default source for tests
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')
source = sim.add_source('Generic', 'Default')
source.particle = 'gamma'
source.energy.mono = 80 * keV
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.n = 200000 / ui.number_of_threads

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'Stats')
s.track_types_flag = True

# create G4 objects
sim.initialize()

# start simulation
# sim.apply_g4_command("/run/verbose 0")
# sim.apply_g4_command("/run/eventModulo 5000 1")
sim.start()

# get results
stats = sim.get_actor('Stats')
print('track type', stats.counts.track_types)

# gate_test4_simulation_stats_actor
# Gate mac/main.mac
stats_ref = gam.read_stat_file(
    pathFile / '..' / 'data' / 'gate' / 'gate_test004_simulation_stats_actor' / 'output' / 'stat.txt')
stats_ref.counts.run_count = sim.user_info.number_of_threads
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.01)

gam.test_ok(is_ok)

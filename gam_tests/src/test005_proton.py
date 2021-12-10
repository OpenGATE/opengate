#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import pathlib
import os

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = 'MersenneTwister'

cm = gam.g4_units('cm')
mm = gam.g4_units('mm')
MeV = gam.g4_units('MeV')

# add a simple volume
waterbox = sim.add_volume('Box', 'Waterbox')
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = 'G4_WATER'

# default source for tests
source = sim.add_source('Generic', 'Default')  # FiXME warning ref not OK (cppSource not the same)
source.particle = 'proton'
source.energy.mono = 150 * MeV
source.position.radius = 10 * mm
source.direction.type = 'momentum'
source.direction.momentum = [0, 0, 1]
source.n = 20000

# add stat actor
sim.add_actor('SimulationStatisticsActor', 'Stats')

# create G4 objects
sim.initialize()

print(sim.dump_sources())
print('Simulation seed:', sim.actual_random_seed)

# verbose
sim.apply_g4_command('/tracking/verbose 0')
# s.g4_com("/run/verbose 2")
# s.g4_com("/event/verbose 2")
# s.g4_com("/tracking/verbose 1")

# start simulation
sim.start()

stats = sim.get_actor('Stats')
print(stats)


# gate_test5_proton
# Gate mac/main.mac
print('-' * 80)
stats_ref = gam.read_stat_file(pathFile / '..' / 'data' / 'gate' / 'gate_test005_proton' / 'output' / 'stat.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.15)

gam.test_ok(is_ok)

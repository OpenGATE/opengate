#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_ge_nm670_spect as gam_spect

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
spect = gam_spect.add_spect(sim, 'spect', debug=False)
psd = 6.11 * cm
spect.translation = [0, 0, -(20 * cm + psd)]

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
cuts.spect.electron = 0.1 * mm
cuts.spect.positron = 0.1 * mm

# default source for tests
activity = 100 * kBq
beam1 = sim.add_source('Generic', 'beam1')
beam1.mother = waterbox.name
beam1.particle = 'gamma'
beam1.energy.mono = 140.5 * keV
beam1.position.type = 'sphere'
beam1.position.radius = 3 * cm
beam1.position.translation = [0, 0, 0 * cm]
beam1.direction.type = 'momentum'
beam1.direction.momentum = [0, 0, -1]
beam1.activity = activity / ui.number_of_threads

# add stat actor
stat = sim.add_actor('SimulationStatisticsActor', 'Stats')
stat.track_types_flag = True

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# stat
gam.warning('Compare stats')
stats = sim.get_actor('Stats')
print(stats)
print(f'Number of runs was {stats.counts.run_count}. Set to 1 before comparison')
stats.counts.run_count = 1  # force to 1
stats_ref = gam.read_stat_file(paths.gate_output_ref / 'stat1.txt')
is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.02)

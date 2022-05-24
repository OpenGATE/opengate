#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.pet_vereos as pet_vereos
import contrib.phantom_necr as phantom_necr

paths = gam.get_default_test_paths(__file__, 'gate_test037_pet')

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.check_volumes_overlap = False

# units
m = gam.g4_units('m')
mm = gam.g4_units('mm')
cm = gam.g4_units('cm')
Bq = gam.g4_units('Bq')
MBq = Bq * 1e6
sec = gam.g4_units('second')

#  change world size
world = sim.world
world.size = [3 * m, 3 * m, 3 * m]

# add a PET VEREOS
pet = pet_vereos.add_pet(sim, 'pet')

# add table
bed = pet_vereos.add_table(sim, 'pet')

# add NECR phantom
phantom = phantom_necr.add_necr_phantom(sim, 'phantom')

# physics
p = sim.get_physics_user_info()
p.physics_list_name = 'G4EmStandardPhysics_option4'
sim.set_cut('world', 'all', 1 * m)
sim.set_cut(phantom.name, 'all', 0.1 * mm)
sim.set_cut(bed.name, 'all', 0.1 * mm)
sim.set_cut(f'{pet.name}_crystal', 'all', 0.1 * mm)

# default source for tests
source = phantom_necr.add_necr_source(sim, phantom)
total_yield = gam.get_rad_yield('F18')
print('Yield for F18 (nb of e+ per decay) : ', total_yield)
source.activity = 3000 * Bq * total_yield
source.activity = 1787.914158 * MBq * total_yield
source.half_life = 6586.26 * sec

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'Stats')
s.track_types_flag = True

# hits and singles collection
# FIXME

# timing
sim.run_timing_intervals = [[0, 0.00001 * sec]]

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# print results
stats = sim.get_actor('Stats')

print(stats)

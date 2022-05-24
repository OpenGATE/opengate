#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_pet as gam_pet
import pathlib

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gam.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = True
ui.check_volumes_overlap = False

# units
m = gam.g4_units('m')
mm = gam.g4_units('mm')
cm = gam.g4_units('cm')
Bq = gam.g4_units('Bq')

#  change world size
world = sim.world
world.size = [3 * m, 3 * m, 3 * m]

# add a PET VEREOS
pet = gam_pet.add_pet(sim, 'pet')

# add table FIXME

# add NECR phantom

# physics
p = sim.get_physics_user_info()
p.physics_list_name = 'G4EmStandardPhysics_option4'
p.enable_decay = True
p.apply_cuts = True  # default
cuts = p.production_cuts
um = gam.g4_units('um')
sim.set_cut('world', 'all', 1 * m)
# sim.set_cut('phantom', 'all', 0.1 * mm)
# sim.set_cut('bed', 'all', 0.1 * mm)
sim.set_cut('pet_crystal', 'all', 0.1 * mm)

# default source for tests
source = sim.add_source('Generic', 'necr_source')
source.particle = 'e+'
source.energy.type = 'F18'
source.position.type = 'sphere'
# source.position.type = 'cylinder' # FIXME
source.position.radius = 1.6 * mm
source.position.translation = [0, 0, 0]
source.direction.type = 'iso'
source.activity = 3 * Bq
# FIXME decay

# add stat actor
s = sim.add_actor('SimulationStatisticsActor', 'Stats')
s.track_types_flag = True

# hits and singles collection
# FIXME

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# print results
stats = sim.get_actor('Stats')

print(stats)

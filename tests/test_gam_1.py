#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from box import Box
from scipy.spatial.transform import Rotation as Rot

# create a simple but complete simulation
s = gam.Simulation(data_folder='data/')

# add a file where material could be read
s.add_material_file('data/a.db')

# change world property
world = s.geometry.world
world.size = [200, 200, 200] # TODO units 100*g4.m
world.material = 'Air'

# add a waterbox
waterbox = s.new_volume('waterbox', 'Box')
waterbox.size = [10, 10, 10] # TODO units
waterbox.translation = [10, 10, 10] # TODO units
waterbox.rotation = Rot.identity().as_matrix() #TODO scipy, np array
waterbox.material = 'Water'

# add a physics list or set_physics_list ?
# how to set cuts ? Cut by region, special cuts
pl = s.set_physics_list('em_opt4')

# add a source
source = s.new_source('source', 'gps')
source.particle = 'gamma'
source.shape = Box()
source.shape.type = 'sphere'
source.shape.radius = 3 # TODO units
source.shape.translation = [100, 0, 0] # TODO units
source.direction = [-1, 0, 0]
source.energy = 6 # TODO units
source.activity = 23 # TODO Bq -> time will be 23 particles per sec

# add a dose scorer
dose = s.new_scorer('dose', 'DoseActor')
dose.filename = 'dose.mhd'
dose.attachTo = 'waterbox'
dose.size_in_voxels = [100, 1, 1]
dose.compute_deposited_energy = True
dose.compute_deposited_energy_uncertainty = True
dose.compute_dose = False

# start simulation
# default: nb of primary
s.start(20)


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam

# create a simulation
# Goal here : placement
simu = gam.Simulation(data_folder='data/')

# change world property
world = simu.geometry.world
world.size = [200, 200, 200] # TODO units 100*g4.m
world.material = 'Air'

# add a box
mybox = simu.new_volume('mybox', 'Box')
mybox.material = 'Water'
mybox.size = [10, 10, 10] # TODO units
mybox.translation = [10, 10, 10] # TODO units
mybox.rotation = Rot.identity().as_matrix() #TODO scipy, np array




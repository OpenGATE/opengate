#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import logging
import os

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

# create a simulation
s = gam.Simulation()

# change world property
world = s.geometry.world
world.half_size = [1, 1, 1] # TODO units

mybox = s.new_volume('mybox', 'Box')
# need for name and type, default mother/material
# default x_half_length ?
# mybox.mother = 'world'
mybox.size = [10, 20, 30]

a = s.new_volume('a', 'Box')
a.mother = 'b'
a.size = [5, 6, 7]

b = s.new_volume('b', 'Box')
b.mother = 'mybox'
b.size = [5, 6, 7]

#v = gam.make_a_volume('titi', 'box', mybox)

# how to get info about Solid  box' ?


print(mybox)

# start simulation (fake for the moment)
s.start()

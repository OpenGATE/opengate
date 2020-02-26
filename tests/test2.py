#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import logging
from box import Box
import os

logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))

# create a simulation
s = gam.Simulation()

# change world property
world = s.geometry.world
world.half_size = [1, 2, 3] # TODO units

# add a volume a
a = s.new_volume('a', 'Box')
a.mother = 'b'
a.size = [5, 6, 7]

# add a volume b
b = s.new_volume('b', 'Box')
b.mother = 'mybox'
b.size = [8, 9, 2]

# add a volume c
c = s.new_volume('c', 'Box')
c.mother = 'b'
c.size = [5, 6, 7]

# add a volume mybox
mybox = s.new_volume('mybox', 'Box')
mybox.size = [10, 20, 30] # TODO units

# add a volume outside new_volume
s.geometry.toto = Box()
s.geometry.toto.name = 'toto'
s.geometry.toto.type = 'TOTO'

#print(s.geometry)

print(f'Volume mybox is {mybox}')

# start simulation (fake for the moment)
s.start()

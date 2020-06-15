#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import numpy as np
from scipy.spatial.transform import Rotation as Rot

# create a simulation
# Goal here : complex geometry
simu = gam.Simulation(data_folder='data/')

# change world property
world = simu.geometry.world
world.size = [200, 200, 200] # TODO units 100*g4.m
world.material = 'Air'

# add a mybox
mybox = simu.new_volume('mybox', 'Box')
mybox.size = [10, 10, 10] # TODO units
mybox.translation = [10, 10, 10] # TODO units
mybox.rotation = Rot.identity().as_matrix() #TODO scipy, np array
mybox.material = 'Water'

# add an insert
insert = simu.new_volume('insert', 'Box')
insert.mother = 'mybox'
insert.size = [10, 10, 10] # TODO units
insert.translation = [10, 10, 10] # TODO units
insert.rotation = Rot.identity().as_matrix() #TODO scipy, np array
insert.material = 'Water'

# add a voxelized volume
def pixel_value_to_material(value):
    if value == 1:
        return 'Air'
    return 'Water'
my_image = simu.new_volume('my_image', 'Image')
my_image.filename = 'toto.mhd'
my_image.translation = [50, 0, 0] # TODO units
my_image.rotation = Rot.identity().as_matrix() #TODO scipy, np array
my_image.material = 'Air'
my_image.material_conversion = pixel_value_to_material

# reference tree
t_ref = '''world Box Air
├── mybox Box Water
│   └── insert Box Water
└── my_image Image Air'''

# check tree
t = simu.dump_volume_tree()
print(t)
if t != t_ref:
    gam.fatal('ERROR Tree is different from reference tree')

simu.initialize()

# reference mybox
mybox_ref = {'mother': 'world',
            'type': 'Box',
            'name': 'mybox',
            'size': [10, 10, 10],
            'translation': [10, 10, 10],
            'rotation': np.array([[1., 0., 0], [0., 1., 0.], [0., 0., 1.]]),
            'material': 'Water',
            'g4': {'solid': 'I am a G4Box'}}

# reference my_image
my_image_ref = {'mother': 'world',
                'type': 'Image',
                'name': 'my_image',
                'filename': 'toto.mhd',
                'translation': [50, 0, 0],
                'rotation': np.array([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]),
                'material': 'Air',
                'material_conversion': pixel_value_to_material}

print(f'Example of constructed mybox {mybox}')


# test
gam.test_dict(mybox_ref, mybox, 'mybox')
gam.test_dict(my_image_ref, my_image, 'my_image')

# end
gam.ok('Tests ok')
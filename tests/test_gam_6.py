#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam2
from box import Box
import geant4 as g4
#import itk

# output
ui = g4.G4UImanager.GetUIpointer()
log = gam2.UIsession()
ui.SetCoutDestination(log)

# create a simple but complete simulation
s = gam2.Simulation()

# test geom
s.geometry.world = Box() #  -> will be w = s.geometry.new('Box', 'World')
world = s.geometry.world
world.name = 'World'
world.size = [4000, 4000, 4000]
world.translation = g4.G4ThreeVector(0, 0, 0)
world.material = 'Air'
world.mother = None

s.geometry.waterbox = Box()
waterbox = s.geometry.waterbox
waterbox.name = 'Waterbox'
waterbox.size = [200, 200, 200]
waterbox.translation = g4.G4ThreeVector(0, 0, 250)
waterbox.material = 'Water'
waterbox.mother = 'World'  # or world

# create G4 objects
s.initialize()

# test A
d = gam2.DoseActor()  # later d = s.new_actor("DoseActor")
#d = g4.GateDoseActor()
ea = s.g4_action.g4_event_action
ea.register_BeginOfEventAction(d)
lv = s.g4_geometry.g4_logical_volumes['Waterbox']
d.RegisterSD(lv)

#PixelType = itk.ctype('float')
#ImageType = itk.Image[PixelType, 3]
#image = ImageType.New()
# Dimension=3
# image = d.GetDoseImage()
# print('image=', image)
# start = itk.Index[Dimension]()
# start[0] = 0  # first index on X
# start[1] = 0  # first index on Y
# start[2] = 0  # first index on Z
# size = itk.Size[Dimension]()
# size[0] = 200  # size along X
# size[1] = 200  # size along Y
# size[2] = 200  # size along Z
# region = itk.ImageRegion[Dimension]()
# region.SetSize(size)
# region.SetIndex(start)
# image.SetRegions(region)
# image.Allocate()
# print(image)

# start simulation
s.start()

print('Dose = ', d.print_debug())
print('end.')

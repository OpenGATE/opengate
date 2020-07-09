#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam2
from box import Box
import geant4 as g4

# import itk


engine = g4.MTwistEngine()
print(engine)
g4.G4Random.setTheEngine(engine)
g4.G4Random.setTheSeeds(4532, 0)
s = g4.G4Random.getTheSeed()
print('seed', s)

# create a simple but complete simulation
s = gam2.Simulation()

# output
ui = g4.G4UImanager.GetUIpointer()
log = gam2.UIsessionSilent()
ui.SetCoutDestination(log)

# test geom
s.geometry.world = Box()  # -> will be w = s.geometry.new('Box', 'World')
world = s.geometry.world
world.name = 'World'
world.size = [4000, 4000, 4000]
world.translation = g4.G4ThreeVector(0, 0, 0)
world.material = 'Air'
world.mother = None

s.geometry.tempobox = Box()
tempobox = s.geometry.tempobox
tempobox.name = 'tempobox'
tempobox.size = [220, 220, 220]  # half size
tempobox.translation = g4.G4ThreeVector(0, 0, 250)
tempobox.material = 'Air'
tempobox.mother = 'World'  # or world

s.geometry.waterbox = Box()
waterbox = s.geometry.waterbox
waterbox.name = 'Waterbox'
waterbox.size = [200, 200, 200]  # half size
waterbox.translation = g4.G4ThreeVector(0, 0, 0)
waterbox.material = 'Water'
waterbox.mother = 'tempobox'  # or world

# WARNING not inherited ! FIXME
s.geometry.insert = Box()
insert = s.geometry.insert
insert.name = 'insert'
insert.size = [100, 100, 100]  # half size
insert.translation = g4.G4ThreeVector(0, 0, 0)
insert.material = 'Water'
insert.mother = 'Waterbox'  # or world

# create G4 objects
s.initialize()

# test A
actor = Box()
actor.name = 'toto'
actor.type = 'Dose'
d = gam2.DoseActor()  # later d = s.new_actor("DoseActor")
actor.g4_actor = d
# d = g4.GateDoseActor()
ea = s.g4_action.g4_event_action
ea.register_actor(actor)
lv = s.g4_geometry.g4_logical_volumes['insert']
d.RegisterSD(lv)
lv = s.g4_geometry.g4_logical_volumes['Waterbox']
d.RegisterSD(lv)
d.batch_size = 10000
d.InitSteps()

# PixelType = itk.ctype('float')
# ImageType = itk.Image[PixelType, 3]
# image = ImageType.New()
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
print('Dose = ', d.PrintDebug())
print('end.')

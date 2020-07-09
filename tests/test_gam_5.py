#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam2
from box import Box
import geant4 as g4

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
waterbox.mother = 'World' # or world

# create G4 objects
s.initialize()

# test A
a = g4.GateAActor()
ea = s.g4_action.g4_event_action
ea.register_BeginOfEventAction(a)
lv = s.g4_geometry.g4_logical_volumes['Waterbox']
a.RegisterSD(lv)

# test B
b = gam2.BActor()
ea.register_BeginOfEventAction(b)
#b.RegisterSD(lv)


#s.actor.dose = Box()
#dose = s.actor.dose
#dose.width = 100

# start simulation
s.start()

print('B = ', b.nb_event, b.nb_step)
print('end.')

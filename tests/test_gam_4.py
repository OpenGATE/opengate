#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam2
from box import Box
import gam_g4 as g4

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

s.initialize()

# test dose
a = g4.GateTestActor()
lv = s.g4_geometry.g4_logical_volumes['Waterbox']
a.RegisterSD(lv)
s.g4_action.eventAction.register_BeginOfEventAction(a)

#s.actor.dose = Box()
#dose = s.actor.dose
#dose.width = 100

# start simulation
s.start()

a.PrintDebug()




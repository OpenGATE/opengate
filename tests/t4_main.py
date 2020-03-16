#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import geant4 as g4
from t4_world import *
from t4_phys import *
from t4_action import *

# --------------------------------------------------------------
# construct the default run manager
runManager = g4.G4RunManager()

# create objects for the main classes
my_world = MyWorld()

# simple physicslist
physicsList = new g4.QBBC
physicsList.SetVerboseLevel(5)

# action initialisation
my_action_init = MyActionInitialization()

# set mandatory initialization classes
runManager.SetUserInitialization(my_world)
runManager.SetUserInitialization(physicsList)
runManager.SetUserInitialization(my_action_init)

# initialize G4 kernel
runManager.Initialize()

# get the pointer to the UI manager and set verbosities
ui = g4.G4UImanager.GetUIpointer()
ui.ApplyCommand("/run/verbose 10")
ui.ApplyCommand("/event/verbose 10")
ui.ApplyCommand("/tracking/verbose 10")

# start a run
numberOfEvent = 3
runManager.BeamOn(numberOfEvent)




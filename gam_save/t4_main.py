#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_g4 as g4
from t4_world import *
#from t4_phys import *
from t4_action import *

# --------------------------------------------------------------
# create objects for the main classes

my_world = MyWorld()
print(f'my_world = {my_world}')

# construct the default run manager
runManager = g4.G4RunManager()
print(f'runManager = {runManager}')

runManager.SetVerboseLevel(0)
runManager.SetUserInitialization(my_world)
print('user init my_world ok')

# simple physicslist
#physicsList = g4.FTFP_BERT(0)
physicsList = g4.QBBC(0, "QBBC") ## first int is verbose 
#physicsList.DumpList()
print(f'physicsList = {physicsList}')

runManager.SetUserInitialization(physicsList)
print('user init physicsList ok')

my_prim_generator = MyPrimaryGeneratorAction()
print(f'my_prim_generator = {my_prim_generator}')

runManager.SetUserAction(my_prim_generator)
print('user init my_prim_generator ok')

# initialize G4 kernel
print('Before Initialize')
runManager.Initialize()
print('After Initialize')

# get the pointer to the UI manager and set verbosity
ui = g4.G4UImanager.GetUIpointer()
ui.ApplyCommand("/run/verbose 2")
ui.ApplyCommand("/event/verbose 2")
ui.ApplyCommand("/tracking/verbose 2")

# start a run
numberOfEvent = 10
print('-------------------------------------------------------------------------> before BeamOn')
runManager.BeamOn(numberOfEvent, None, -1)
print('after BeamOn')

# The following allow to remove the final warning
gm = g4.G4GeometryManager.GetInstance().OpenGeometry(None)




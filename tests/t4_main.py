#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import geant4 as g4
from t4_world import *
#from t4_phys import *
from t4_action import *

# --------------------------------------------------------------
# create objects for the main classes
my_world = MyWorld()
print(f'my_world = {my_world}')

# simple physicslist
#physicsList = g4.QBBC()
#print(f'physicsList = {physicsList}')

# construct the default run manager
runManager = g4.G4RunManager()
print(f'runManager = {runManager}')

# action initialisation
#my_action_init = MyActionInitialization()
#print(f'my_action_init = {my_action_init}')

# set mandatory initialization classes
runManager.SetUserInitialization(my_world)
runManager.SetVerboseLevel(10)
print('user init my_workd ok')

#runManager.SetUserInitialization(physicsList)
#print('user init physicsList ok')

#particle_table = g4.G4ParticleTable.GetParticleTable()
#print(f'particle_table {particle_table}')
#particle_table.CreateAllParticles()

#my_prim_generator = MyPrimaryGeneratorAction()
#print(f'my_prim_generator = {my_prim_generator}')

#runManager.SetUserInitialization(my_action_init)
#print('user init my_action_init ok')

#runManager.SetUserAction(my_prim_generator)
#print('user init my_prim_generator ok')


# initialize G4 kernel
print('')
print('Before Initialize')
runManager.Initialize()
print('After Initialize')

# get the pointer to the UI manager and set verbosities
ui = g4.G4UImanager.GetUIpointer()
ui.ApplyCommand("/run/verbose 10")
ui.ApplyCommand("/event/verbose 10")
ui.ApplyCommand("/tracking/verbose 10")

# start a run
numberOfEvent = 3
runManager.BeamOn(numberOfEvent)




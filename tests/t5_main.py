#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
from t5_world import *
from t5_action import *
import geant4 as g4
import matplotlib.pyplot as plt
import time

# random
# FIXME !!! ---> bad alloc somewhere in release mode (after end)
engine = g4.MTwistEngine()
print(engine)
g4.G4Random.setTheEngine(engine)
g4.G4Random.setTheSeeds(4532, 0)
s = g4.G4Random.getTheSeed()
print('seed', s)
#print('status', g4.G4Random.showEngineStatus())
#exit(0)

# Geometry
my_world = MyWorld()
print(f'my_world = {my_world}')

# Run manager
runManager = g4.G4RunManager()
runManager.SetVerboseLevel(0)
runManager.SetUserInitialization(my_world)
print(f'runManager = {runManager}')

# Physics list
print('here')
physicsList = g4.QBBC(0, "QBBC") ## first int is verbose #FIXME bad alloc here also
print('end')
print('dir', physicsList.GetPhysicsTableDirectory())
# exit(0)
#physicsList = g4.QGS_BIC(0)
#physicsList.DumpList()
runManager.SetUserInitialization(physicsList)
print(f'physicsList = {physicsList}')

# Action and source
actions = B1ActionInitialization()
print(f'actions {actions}')
runManager.SetUserInitialization(actions)

# Source
#my_prim_generator = MyPrimaryGeneratorAction()
#runManager.SetUserAction(my_prim_generator)
#print(f'my_prim_generator = {my_prim_generator}')
#print('user init my_prim_generator ok')

# Initialization
print('Before Initialize')
runManager.Initialize()
print('After Initialize')

# UI manager and  verbosity
ui = g4.G4UImanager.GetUIpointer()
ui.ApplyCommand("/run/verbose 2")
#ui.ApplyCommand("/event/verbose 2")
#ui.ApplyCommand("/tracking/verbose 1")

# start a run
numberOfEvent = 30000 #00
print('-------------------------------------------------------------------------> before BeamOn')
start = time.time()
runManager.BeamOn(numberOfEvent, None, -1)
print('after BeamOn')
end = time.time()
print('Timing', end - start)

# get the 1D dose
ddose = actions.get_dose()
exit(0)

fig, ax = plt.subplots()
ax.plot(ddose)
plt.show()

# The following allow to remove the final warning
print('close geom')
gm = g4.G4GeometryManager.GetInstance().OpenGeometry(None)
print('final end.')



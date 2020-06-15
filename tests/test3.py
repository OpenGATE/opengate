#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pint
import numpy as np

print('hello')

u = pint.UnitRegistry()

x = np.array([10.0, 20, 5])*u.cm
y = np.array([10.0, 20, 5])*u.m

print(x, y, x+y)

'''
Fred
 - FrameOfReference = origin + vector --> no, use G4
 - Scorer / PhysicaLRegion / Source etc as classes
 - Simulation object, addComponent, addSource
 - Engine -> to run
'''

'''
GAM
 - almost everyting is a Box
 - Simulation class
 
'''




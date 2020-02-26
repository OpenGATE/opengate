#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print('hello world')

import Geant4 as g4
#from Geant4 import G4interface


print('hello world')

v = g4.G4ThreeVector(2)
print('v =',v)
print('v.x =', v.x)
v.x = 1
v.y = 5
v.z = 4
print('v=', v)
print(f'v mag = {v.mag()}')

w = g4.G4ThreeVector(v)
print(f'w = {w}')
w.x = 6
w.y = 5
w.z = 4
print(f'w = {w}')

print(f'2*v = {2*v}')
print(f'v.w = {v*w}')
v -= w
print(f'v -= w -> {v}')

v[0] = 666
print(v)
try:
    v[40] = 12
    print(v)
    print(v[12])
    print(v[40])
except:
    print('Index error ok')


print('tol', g4.G4ThreeVector.getTolerance())

# overloaded
# help(v.isNear)
print('is near', v.isNear(w, 20))
print('is near', v.isNear(w))


s = g4.G4String()
s = 'titi'
print('G4String = ', s, type(s))
s = g4.G4String('tutu')
print('G4String = ', s, type(s))


r = g4.G4RunManager()
print(r)
#r.RestoreRandomNumberStatus("toto")

r.Initialize()


# test class to create a Box
# test class to create an Image

# how to test ?
# class box, create ?

# simu = gate.Simulation(name='mysimu', data_folder='data/')

# simu.geometry = Box() #force error

# print(simu)

# simu.start()



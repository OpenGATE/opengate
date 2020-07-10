#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_g4 as g4

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



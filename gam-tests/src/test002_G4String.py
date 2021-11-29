#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import gam_g4 as g4

a = 'titi'
s = g4.G4String(a)
print('G4String =', s, type(s))
assert s == 'titi'
assert type(s) == gam.g4.G4String

t = g4.G4String(s)
print('G4String =', t, type(t))
assert t == 'titi'

t = 'toto'
print(f's={s} t={t} ', type(t))

assert s == 'titi'
assert t == 'toto'

gam.test_ok(True)

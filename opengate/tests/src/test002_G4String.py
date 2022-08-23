#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4

a = "titi"
s = g4.G4String(a)
print("G4String =", s, type(s))
assert s == "titi"
assert type(s) == gate.g4.G4String

t = g4.G4String(s)
print("G4String =", t, type(t))
assert t == "titi"

t = "toto"
print(f"s={s} t={t} ", type(t))

assert s == "titi"
assert t == "toto"

gate.test_ok(True)

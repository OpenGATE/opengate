#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate.tests.utility as utility
import numpy as np
import opengate_core as g4
from box import Box
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    v = g4.G4ThreeVector(2)
    print("v =", v)
    assert v == g4.G4ThreeVector(2, 0, 0)

    print("v.x =", v.x)
    v.x = 1
    v.y = 5
    v.z = 4
    print("v=", v)
    assert v == g4.G4ThreeVector(1, 5, 4)

    print(f"v mag = {v.mag()}")
    np.testing.assert_almost_equal(v.mag(), 6.48074069840786)

    w = g4.G4ThreeVector(v)
    print(f"w = {w}")
    assert v == w
    w.x = 6
    w.y = 5
    w.z = 4
    print(f"w = {w}")
    assert w == g4.G4ThreeVector(6, 5, 4)
    assert v == g4.G4ThreeVector(1, 5, 4)

    print(f"2*v = {2 * v}")
    assert 2 * v == g4.G4ThreeVector(2, 10, 8)

    print(f"v.w = {v * w}")
    assert v * w == 47.0

    v -= w
    print(f"v -= w -> {v}")
    assert v == g4.G4ThreeVector(-5, 0, 0)

    v[0] = 666
    print(v)
    try:
        v[40] = 12
        print(v)
        print(v[12])
        print(v[40])
    except:
        print("Index error ok")

    print("tol", g4.G4ThreeVector.getTolerance())

    # overloaded
    # help(v.isNear)
    print("is near", v.isNear(w, 20))
    assert v.isNear(w, 20) == True

    print("is near", v.isNear(w))
    assert v.isNear(w) == False

    # compare numpy matrix copied to G4.
    u = Box()
    r1 = Rotation.from_euler("y", 23, degrees=True)
    r2 = Rotation.from_euler("x", 66, degrees=True)
    u.mat = (r2 * r1).as_matrix()
    g4_m = g4.DictGetG4RotationMatrix(u, "mat")

    is_ok = True

    def compare(a, b):
        for i in range(3):
            if not np.isclose(a[i], b[i]):
                print("Matrices are not egal")
                print(u.mat)
                print(g4_m)
                return False
            return True

    print("np matrix", u.mat)
    print("G4 matrix", g4_m)
    is_ok = compare(u.mat[0], g4_m.rowX()) and is_ok
    is_ok = compare(u.mat[1], g4_m.rowY()) and is_ok
    is_ok = compare(u.mat[2], g4_m.rowZ()) and is_ok
    utility.print_test(is_ok, "Matrix comparison")

    utility.test_ok(is_ok)

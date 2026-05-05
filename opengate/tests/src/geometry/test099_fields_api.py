#!/usr/bin/env python3
"""
Test 099 — Field API tests.

Checks the following behaviours:
  1. add_field() before volume is added to simulation -> fatal
  2. Duplicate field on same volume -> fatal
  3. Two different fields with same name -> fatal
  4. Same field on two volumes -> OK
  5. Custom field with non-callable -> TypeError
  6. Custom field with wrong component count -> ValueError
"""

import opengate as gate
from opengate.geometry import fields
from opengate.geometry.volumes import VolumeBase
from opengate.tests import utility

from test099_fields_helpers import g4_tesla, g4_m, g4_cm


def _expect_error(fn, error_msg):
    """Run fn, expect an exception (fatal() raises Exception, others raise specific types)."""
    try:
        fn()
        print(f"  FAIL — expected error: {error_msg}")
        return False
    except Exception as e:
        print(f"  OK — got {type(e).__name__}: {error_msg}")
        return True


if __name__ == "__main__":
    is_ok = True

    # 1. add_field before volume is in simulation
    print("Test: add_field before volume added to simulation")
    orphan_box = gate.geometry.volumes.BoxVolume(name="orphan")
    orphan_box.size = [10 * g4_cm, 10 * g4_cm, 10 * g4_cm]
    field = fields.UniformMagneticField(name="B_orphan")
    field.field_vector = [0, 0, 1 * g4_tesla]
    ok = _expect_error(
        lambda: orphan_box.add_field(field),
        "add_field on orphan volume",
    )
    is_ok = is_ok and ok

    # 2. Duplicate field on same volume
    print("Test: duplicate field on same volume")
    sim = gate.Simulation()
    sim.world.size = [2 * g4_m, 2 * g4_m, 2 * g4_m]
    sim.world.material = "G4_Galactic"
    box = sim.add_volume("BoxVolume", "box")
    box.size = [10 * g4_cm, 10 * g4_cm, 10 * g4_cm]
    box.material = "G4_Galactic"

    f1 = fields.UniformMagneticField(name="B1")
    f1.field_vector = [0, 0, 1 * g4_tesla]
    box.add_field(f1)

    f2 = fields.UniformMagneticField(name="B2")
    f2.field_vector = [0, 1 * g4_tesla, 0]
    ok = _expect_error(
        lambda: box.add_field(f2),
        "second field on same volume",
    )
    is_ok = is_ok and ok

    # 3. Two different fields with same name
    print("Test: name collision between different field objects")
    sim = gate.Simulation()
    sim.world.size = [2 * g4_m, 2 * g4_m, 2 * g4_m]
    sim.world.material = "G4_Galactic"

    box_a = sim.add_volume("BoxVolume", "box_a")
    box_a.size = [10 * g4_cm, 10 * g4_cm, 10 * g4_cm]
    box_a.material = "G4_Galactic"
    box_a.translation = [-20 * g4_cm, 0, 0]

    box_b = sim.add_volume("BoxVolume", "box_b")
    box_b.size = [10 * g4_cm, 10 * g4_cm, 10 * g4_cm]
    box_b.material = "G4_Galactic"
    box_b.translation = [20 * g4_cm, 0, 0]

    fa = fields.UniformMagneticField(name="B_same_name")
    fa.field_vector = [0, 0, 1 * g4_tesla]
    box_a.add_field(fa)

    fb = fields.UniformMagneticField(name="B_same_name")
    fb.field_vector = [0, 1 * g4_tesla, 0]
    ok = _expect_error(
        lambda: box_b.add_field(fb),
        "name collision",
    )
    is_ok = is_ok and ok

    # 4. Same field on two volumes (should be ok)
    print("Test: same field on two volumes")
    sim = gate.Simulation()
    sim.world.size = [2 * g4_m, 2 * g4_m, 2 * g4_m]
    sim.world.material = "G4_Galactic"

    box1 = sim.add_volume("BoxVolume", "box1")
    box1.size = [10 * g4_cm, 10 * g4_cm, 10 * g4_cm]
    box1.material = "G4_Galactic"
    box1.translation = [-20 * g4_cm, 0, 0]

    box2 = sim.add_volume("BoxVolume", "box2")
    box2.size = [10 * g4_cm, 10 * g4_cm, 10 * g4_cm]
    box2.material = "G4_Galactic"
    box2.translation = [20 * g4_cm, 0, 0]

    shared = fields.UniformMagneticField(name="B_shared")
    shared.field_vector = [0, 0, 1 * g4_tesla]
    try:
        box1.add_field(shared)
        box2.add_field(shared)
        ok = (
            shared.attached_to == ["box1", "box2"]
            and box1.field == "B_shared"
            and box2.field == "B_shared"
        )
        print(f"  {'OK' if ok else 'FAIL'} — same field on two volumes")
    except Exception as e:
        print(f"  FAIL — unexpected error: {e}")
        ok = False
    is_ok = is_ok and ok

    # 5. Custom field with non-callable
    print("Test: custom field with non-callable field_function")
    f = fields.CustomMagneticField(name="B_bad")
    f.field_function = "i'm a string, not a function! will i fool you?"
    ok = _expect_error(
        lambda: f._create_field(),
        "non-callable field_function",
    )
    is_ok = is_ok and ok

    # 6. Custom field with wrong component count
    print("Test: custom B field returning 6 components instead of 3")
    f = fields.CustomMagneticField(name="B_wrong_dims")
    f.field_function = lambda x, y, z, t: [0, 0, 0, 0, 0, 0]
    ok = _expect_error(
        lambda: f._create_field(),
        "wrong component count",
    )
    is_ok = is_ok and ok

    utility.test_ok(is_ok)

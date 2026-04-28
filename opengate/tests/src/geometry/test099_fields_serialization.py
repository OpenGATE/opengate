#!/usr/bin/env python3
"""
Test 099 — Field serialization round-trip.

Tests that non-custom field types survive serialization
and that custom fields correctly refuse it.
"""

import opengate as gate
from opengate.geometry import fields
from opengate.tests import utility

from test099_fields_helpers import g4_tesla, g4_m, g4_cm, g4_mm, g4_volt


def _make_sim_with_box():
    """Create a minimal simulation with one box volume."""
    sim = gate.Simulation()
    sim.number_of_threads = 1
    world = sim.world
    world.size = [2 * g4_m, 2 * g4_m, 2 * g4_m]
    world.material = "G4_Galactic"

    box = sim.add_volume("BoxVolume", "box")
    box.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
    box.material = "G4_Galactic"
    return sim, box


if __name__ == "__main__":
    is_ok = True

    # Uniform magnetic field round-trip
    sim, box = _make_sim_with_box()
    field = fields.UniformMagneticField(name="B_uniform")
    field.field_vector = [0, 1 * g4_tesla, 0]
    field.delta_chord = 0.5 * g4_mm
    box.add_field(field)

    d = sim.to_dictionary()
    assert "fields" in d["volume_manager"]
    assert "B_uniform" in d["volume_manager"]["fields"]
    fd = d["volume_manager"]["fields"]["B_uniform"]
    assert fd["object_type"] == "UniformMagneticField"
    assert fd["attached_to"] == ["box"]
    assert fd["user_info"]["field_vector"] == [0, 1 * g4_tesla, 0]

    sim2 = gate.Simulation()
    sim2.from_dictionary(d)
    restored = sim2.volume_manager.fields["B_uniform"]
    ok = (
        isinstance(restored, fields.UniformMagneticField)
        and restored.field_vector == [0, 1 * g4_tesla, 0]
        and restored.delta_chord == 0.5 * g4_mm
        and restored.attached_to == ["box"]
        and sim2.volume_manager.volumes["box"].field == "B_uniform"
    )
    is_ok = is_ok and ok
    print(f"Uniform B round-trip: {'OK' if ok else 'FAIL'}")

    # Quadrupole round-trip
    sim, box = _make_sim_with_box()
    field = fields.QuadrupoleMagneticField(name="B_quad")
    field.gradient = 10 * g4_tesla / g4_m
    box.add_field(field)

    d = sim.to_dictionary()
    sim2 = gate.Simulation()
    sim2.from_dictionary(d)
    restored = sim2.volume_manager.fields["B_quad"]
    ok = (
        isinstance(restored, fields.QuadrupoleMagneticField)
        and restored.gradient == 10 * g4_tesla / g4_m
        and restored.attached_to == ["box"]
    )
    is_ok = is_ok and ok
    print(f"Quadrupole round-trip: {'OK' if ok else 'FAIL'}")

    # Uniform electric field round-trip
    sim, box = _make_sim_with_box()
    field = fields.UniformElectricField(name="E_uniform")
    field.field_vector = [0, 0, 1e6 * g4_volt / g4_m]
    box.add_field(field)

    d = sim.to_dictionary()
    sim2 = gate.Simulation()
    sim2.from_dictionary(d)
    restored = sim2.volume_manager.fields["E_uniform"]
    ok = (
        isinstance(restored, fields.UniformElectricField)
        and restored.field_vector == [0, 0, 1e6 * g4_volt / g4_m]
        and restored.attached_to == ["box"]
    )
    is_ok = is_ok and ok
    print(f"Uniform E round-trip: {'OK' if ok else 'FAIL'}")

    # Custom fields refuse serialization
    field = fields.CustomMagneticField(name="B_custom")
    field.field_function = lambda x, y, z, t: [0, 0, 0]
    try:
        field.to_dictionary()
        ok = False  # should not reach here
    except NotImplementedError:
        ok = True
    is_ok = is_ok and ok
    print(f"Custom B serialization raises: {'OK' if ok else 'FAIL'}")

    field = fields.CustomElectricField(name="E_custom")
    field.field_function = lambda x, y, z, t: [0, 0, 0]
    try:
        field.to_dictionary()
        ok = False
    except NotImplementedError:
        ok = True
    is_ok = is_ok and ok
    print(f"Custom E serialization raises: {'OK' if ok else 'FAIL'}")

    # Multiple volume attachment round-trip
    sim = gate.Simulation()
    sim.number_of_threads = 1
    sim.world.size = [2 * g4_m, 2 * g4_m, 2 * g4_m]
    sim.world.material = "G4_Galactic"

    box1 = sim.add_volume("BoxVolume", "box1")
    box1.size = [20 * g4_cm, 20 * g4_cm, 20 * g4_cm]
    box1.material = "G4_Galactic"
    box1.translation = [-30 * g4_cm, 0, 0]

    box2 = sim.add_volume("BoxVolume", "box2")
    box2.size = [20 * g4_cm, 20 * g4_cm, 20 * g4_cm]
    box2.material = "G4_Galactic"
    box2.translation = [30 * g4_cm, 0, 0]

    field = fields.UniformMagneticField(name="B_shared")
    field.field_vector = [0, 0, 2 * g4_tesla]
    box1.add_field(field)
    box2.add_field(field)

    d = sim.to_dictionary()
    sim2 = gate.Simulation()
    sim2.from_dictionary(d)
    restored = sim2.volume_manager.fields["B_shared"]
    ok = (
        set(restored.attached_to) == {"box1", "box2"}
        and sim2.volume_manager.volumes["box1"].field == "B_shared"
        and sim2.volume_manager.volumes["box2"].field == "B_shared"
    )
    is_ok = is_ok and ok
    print(f"Multi-volume round-trip: {'OK' if ok else 'FAIL'}")

    utility.test_ok(is_ok)

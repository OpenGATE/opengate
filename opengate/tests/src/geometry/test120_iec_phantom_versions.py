#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The NEMA IEC body phantom exists in two versions, named after their total length:
- iec_214 (default, GATE 10): 10 mm top and bottom walls,
- iec_220 (GATE 9, GateContrib NEMA_IEC_2001.mac): 3 mm top and bottom walls.
In both, the sphere centres are 70 mm below the inside of the lid (NEMA).
Check the dimensions of both versions, the default sphere centres, and that the
geometry has no overlaps.
"""

import numpy as np

import opengate as gate
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate.tests import utility

mm = gate.g4_units.mm

expected = {
    # total length, interior length, z of the sphere centres (mm)
    "iec_214": (214, 194, 27),
    "iec_220": (220, 214, 37),
}


def check_version(version):
    sim = gate.Simulation()
    sim.check_volumes_overlap = True
    sim.init_only = True
    sim.world.size = [1 * gate.g4_units.m] * 3
    name = f"iec_{version}"
    gate_iec.add_iec_phantom(sim, name, check_overlap=True, version=version)

    total, interior, sphere_z = expected[version]
    vm = sim.volume_manager.volumes
    is_ok = True

    # total length: z extent of the phantom; interior length: the central
    # cylinder spans the whole interior
    lower, upper = vm[name].bounding_limits
    length = (upper[2] - lower[2]) / mm
    interior_length = 2 * vm[f"{name}_center_cylinder"].dz / mm
    b = np.isclose(length, total) and np.isclose(interior_length, interior)
    utility.print_test(
        b, f"{version}: total length {length} mm, interior length {interior_length} mm"
    )
    is_ok = is_ok and b

    # sphere centres: 70 mm below the inside of the lid (NEMA)
    centers, _ = gate_iec.compute_sphere_centers_and_volumes(sim, name)
    zs = [c[2] / mm for c in centers]
    lid_to_spheres = interior_length / 2 - np.array(zs)
    b = np.allclose(zs, sphere_z) and np.allclose(lid_to_spheres, 70)
    utility.print_test(
        b, f"{version}: spheres at z={zs[0]} mm, {lid_to_spheres[0]} mm below the lid"
    )
    is_ok = is_ok and b

    # the default sphere centres (used without building the phantom) agree
    default_centers, _ = gate_iec.get_default_sphere_centers_and_volumes(version)
    b = np.allclose(
        sorted(tuple(c) for c in default_centers),
        sorted(tuple(np.array(c) / mm) for c in centers),
        atol=1e-4,
    )
    utility.print_test(b, f"{version}: default sphere centres match the geometry")
    is_ok = is_ok and b

    # the capillaries end exactly at the inside of the lid
    for d in ["10mm", "37mm"]:
        cap = vm[f"{name}_capillary_{d}"]
        top = (cap.translation[2] + cap.dz) / mm
        b = np.isclose(top, interior_length / 2)
        utility.print_test(b, f"{version}: capillary {d} ends at the lid ({top} mm)")
        is_ok = is_ok and b

    # build the geometry in Geant4, with the overlap check
    sim.run(start_new_process=True)
    utility.print_test(True, f"{version}: geometry built, no overlap reported")
    return is_ok


if __name__ == "__main__":
    is_ok = True
    for version in ["iec_214", "iec_220"]:
        is_ok = check_version(version) and is_ok

    # the default is the GATE 10 version
    b = gate_iec.default_iec_version == "iec_214"
    utility.print_test(b, "Default version is iec_214")
    is_ok = is_ok and b

    # an unknown version is refused
    try:
        gate_iec.get_iec_dimensions("iec_999")
        b = False
    except Exception:
        b = True
    utility.print_test(b, "Unknown version is refused")
    is_ok = is_ok and b

    utility.test_ok(is_ok)

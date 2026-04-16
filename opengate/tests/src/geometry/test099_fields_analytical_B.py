#!/usr/bin/env python3
"""
Test 099 — Uniform magnetic field: analytical validation.

A proton enters a region with uniform B along Y.
Checks:
  1. Circular trajectory in XZ plane (cyclotron radius)
  2. No deflection in Y
  3. Energy conservation (B does no work)
"""

import numpy as np
import uproot

from opengate.geometry import fields
from opengate.tests import utility

from test099_fields_helpers import (
    g4_tesla,
    g4_mm,
    g4_MeV,
    g4_eplus,
    PROTON_MASS,
    cyclotron_radius,
    build_field_simulation,
)

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test099_fields"
    )

    By = 5 * g4_tesla
    T = 10 * g4_MeV

    field = fields.UniformMagneticField(name="B_uniform")
    field.field_vector = [0, By, 0]

    sim, phsp = build_field_simulation(
        field,
        kinetic_energy=T,
        phsp_output_filename=paths.output / "test099_analytical_B.root",
        output_dir=paths.output,
    )
    sim.run()

    # Read results
    df = uproot.open(str(paths.output / "test099_analytical_B.root"))["phsp;1"].arrays(
        library="pd"
    )

    # Analytical expectation
    r = cyclotron_radius(T, By, PROTON_MASS, 1 * g4_eplus)

    # Entry point & circle centre
    box_half_z = 50 * g4_mm / 2 * 10
    x0, y0, z0 = 0.0, 0.0, -box_half_z
    cx, cz = x0 - r, z0

    x_exit = df["PostPosition_X"].values
    y_exit = df["PostPosition_Y"].values
    z_exit = df["PostPosition_Z"].values
    KE_exit = df["PostKineticEnergy"].values

    # Check 1: circular trajectory
    r_TOL = 1e-3 * g4_mm
    residual = np.sqrt((x_exit - cx) ** 2 + (z_exit - cz) ** 2) - r
    is_ok_circular = np.all(np.abs(residual) < r_TOL)
    print(f"Circle-fit residual: {residual}")
    print(f"Circular trajectory OK: {is_ok_circular}")

    # Check 2: no Y deflection
    is_ok_y = np.all(np.abs(y_exit - y0) < r_TOL)
    print(f"No Y deflection OK: {is_ok_y}")

    # Check 3: energy conservation
    e_TOL = 0.01 * g4_MeV
    is_ok_energy = np.all(np.abs(KE_exit - T) < e_TOL)
    print(f"Energy conservation OK: {is_ok_energy}  (dKE = {KE_exit - T})")

    is_ok = is_ok_circular and is_ok_y and is_ok_energy
    utility.test_ok(is_ok)

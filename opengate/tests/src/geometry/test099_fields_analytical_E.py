#!/usr/bin/env python3
"""
Test 099 — Uniform electric field: analytical validation.

A proton enters a region with uniform E along X.
Checks:
  1. Displacement consistent with energy gain: dx = dKE / (qE)
  2. No deflection in Y
  3. Energy gain matches work done: dKE = q * E * dx
"""

import numpy as np
import uproot

from opengate.geometry import fields
from opengate.tests import utility

from test099_fields_helpers import (
    g4_m,
    g4_mm,
    g4_MeV,
    g4_volt,
    g4_eplus,
    PROTON_MASS,
    build_field_simulation,
)

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test099_fields")

    Ex = 1e8 * g4_volt / g4_m
    T = 10 * g4_MeV

    field = fields.UniformElectricField(name="E_uniform")
    field.field_vector = [Ex, 0, 0]

    sim, phsp = build_field_simulation(
        field,
        kinetic_energy=T,
        phsp_output_filename=paths.output / "test099_analytical_E.root",
        output_dir=paths.output,
    )
    sim.run()

    df = uproot.open(str(paths.output / "test099_analytical_E.root"))["phsp;1"].arrays(
        library="pd"
    )

    q = 1 * g4_eplus
    x_exit = df["PostPosition_X"].values
    y_exit = df["PostPosition_Y"].values
    KE_exit = df["PostKineticEnergy"].values
    r_TOL = 0.01 * g4_mm
    e_TOL = 0.01 * g4_MeV

    # Check 1: x displacement consistent with energy gain
    x_from_energy = (KE_exit - T) / (q * Ex)
    is_ok_x = np.all(np.abs(x_exit - x_from_energy) < r_TOL)
    print(f"x consistency OK: {is_ok_x}  (residual = {x_exit - x_from_energy})")

    # Check 2: no Y deflection
    is_ok_y = np.all(np.abs(y_exit) < r_TOL)
    print(f"No Y deflection OK: {is_ok_y}")

    # Check 3: energy gain = qE * dx
    KE_expected = T + q * Ex * x_exit / g4_MeV
    is_ok_energy = np.all(np.abs(KE_exit - KE_expected) < e_TOL)
    print(f"Energy gain OK: {is_ok_energy}  (residual = {KE_exit - KE_expected})")

    is_ok = is_ok_x and is_ok_y and is_ok_energy
    utility.test_ok(is_ok)

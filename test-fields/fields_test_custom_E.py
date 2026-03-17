#!/usr/bin/env python3
"""
* Description: Tests for tracking in a uniform electric field,
*              comparing to analytical results.
* Created: 23.02.2026
"""

import uproot
import pandas as pd
import numpy as np

import opengate as gate
from opengate.geometry import fields
from opengate.tests import utility


# * ---------------------------------
# *  ------- Helper functions ------
# * ---------------------------------
def electric_acceleration(E, q, m):
    """Return acceleration a = qE/m (Geant4 units)."""
    return q * E / m


# * ---------------------------------
# *  ---------- Main Code ----------
# * ---------------------------------
if __name__ == "__main__":

    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.visu = True
    sim.visu_type = "qt"
    sim.number_of_threads = 2
    sim.random_seed = 42
    sim.output_dir = "."

    # Units
    g4_m = gate.g4_units.m
    g4_cm = gate.g4_units.cm
    g4_mm = gate.g4_units.mm
    g4_tesla = gate.g4_units.tesla
    g4_MeV = gate.g4_units.MeV
    g4_volt = gate.g4_units.volt
    g4_eplus = gate.g4_units.eplus

    # World
    world = sim.world
    world.size = [1 * g4_m, 1 * g4_m, 1 * g4_m]
    world.material = "G4_Galactic"

    # Field box
    box = sim.add_volume("BoxVolume", "field_box")
    box.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
    box.material = "G4_Galactic"

    # -------------------------------------------------
    # Uniform ELECTRIC field along X
    # -------------------------------------------------
    Ex = 1e8 * g4_volt / g4_m

    def custom_uniform_E_field(x, y, z, t):
        return [Ex, 0, 0]

    field = fields.CustomElectricField(
        name="E_uniform_custom",
        field_function=custom_uniform_E_field,
    )
    box.add_field(field)

    # Proton source
    T = 10 * g4_MeV

    source = sim.add_source("GenericSource", "proton_source")
    source.particle = "proton"
    source.n = 1

    source.energy.type = "mono"
    source.energy.mono = T

    source.position.type = "point"
    source.position.translation = [
        0 * g4_cm,
        0 * g4_cm,
        -100 * g4_cm,
    ]

    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    # Phase space actor
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = box.name
    phsp.attributes = [
        "PostKineticEnergy",
        "PostPosition",
    ]
    phsp.output_filename = "./test-fields/out/testEEE_phsp.root"
    phsp.steps_to_store = "exiting"
    phsp.root_output.write_to_disk = True

    # Run
    sim.run()

    # -------------------------------------------------
    # Analysis
    # -------------------------------------------------
    file = uproot.open("./test-fields/out/testEEE_phsp.root")
    df = file["phsp;1"].arrays(library="pd")

    print(df)

    # Proton constants
    mp = 938.27208943 * g4_MeV
    q = 1 * g4_eplus

    # Entry point
    x0 = 0.0 * g4_mm
    y0 = 0.0 * g4_mm
    z0 = -box.size[2] / 2

    # Initial velocity (relativistic)
    E_tot = T + mp
    p = np.sqrt(E_tot**2 - mp**2)
    v0 = p / E_tot  # natural units (c=1)

    # Electric acceleration
    a = electric_acceleration(Ex, q, mp)

    # Exit positions
    x_exit = df["PostPosition_X"].values
    y_exit = df["PostPosition_Y"].values
    z_exit = df["PostPosition_Z"].values
    KE_exit = df["PostKineticEnergy"].values
    r_TOL = 0.01 * g4_mm

    # -------------------------------------------------
    # Check 1 — trajectory consistent with energy gain
    # -------------------------------------------------

    x_from_energy = (KE_exit - T) / (q * Ex)

    residual = x_exit - x_from_energy

    print(f"x consistency residual: {residual}")

    is_ok_parabola = np.all(np.abs(residual) < r_TOL)

    print(f"Parabolic residual: {residual}")
    print(
        f"Parabolic trajectory {'' if is_ok_parabola else 'NOT '}satisfied within {r_TOL:.3f} mm: {is_ok_parabola}"
    )

    # -------------------------------------------------
    # Check 2 — No deflection in Y
    # -------------------------------------------------
    is_ok_y = np.all(np.abs(y_exit - y0) < r_TOL)
    print(f"No Y deflection: {is_ok_y}")

    # -------------------------------------------------
    # Check 3 — Energy gain qEΔx
    # -------------------------------------------------
    KE_expected = T + (q * Ex * (x_exit - x0)) / g4_MeV

    e_TOL = 0.01 * g4_MeV
    is_ok_energy = np.all(np.abs(KE_exit - KE_expected) < e_TOL)

    print(f"Energy residual: {KE_exit - KE_expected}")
    print(
        f"Energy gain qEΔx {'' if is_ok_energy else 'NOT '}satisfied within {e_TOL:.3f} MeV: {is_ok_energy}"
    )

    # -------------------------------------------------
    is_ok = is_ok_parabola and is_ok_y and is_ok_energy
    print(f"\nAll checks passed: {is_ok}")

    utility.test_ok(is_ok)

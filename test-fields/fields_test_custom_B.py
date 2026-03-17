#!/usr/bin/env python3
"""
* Description: Tests for tracking in a uniform magnetic field, comparing to analytical results.
* Created: 23.02.2026
"""

from calendar import c

import uproot
import pandas as pd
import numpy as np

import opengate as gate
from opengate.geometry import fields
from opengate.tests import utility


# * ---------------------------------
# *  ------- Helper functions ------
# * ---------------------------------
def cyclotron_radius(T, B, m, q):
    """
    Calculate the cyclotron radius using Geant4 units.
    Inputs:
        T : kinetic energy (Geant4 units, e.g. MeV)
        B : magnetic field (Geant4 units, e.g. tesla)
        m : mass (Geant4 units, e.g. MeV)
        q : charge (Geant4 units, e.g. eplus)
    Returns:
        radius in meters (Geant4 units)
    """
    E = T + m  # total energy
    p = (E**2 - m**2) ** 0.5
    r_metres = p / (q * B * 0.299792458)
    return r_metres / g4_m


# * ---------------------------------


# * ---------------------------------
# *  ---------- Main Code ----------
# * ---------------------------------
if __name__ == "__main__":
    # paths = utility.get_default_test_paths(
    #     __file__, "gate_testBBB_fields_uniform_B", output_folder="testBBB"
    # )

    # * -----------------------------------------------------------
    # *  ------- Simulation with the Custom Magnetic Field -------
    # * -----------------------------------------------------------
    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.number_of_threads = 2
    sim.random_seed = 42
    sim.check_volumes_overlap = True
    sim.output_dir = "."  # paths.output

    g4_m = gate.g4_units.m
    g4_cm = gate.g4_units.cm
    g4_mm = gate.g4_units.mm
    g4_mrad = gate.g4_units.mrad
    g4_tesla = gate.g4_units.tesla
    g4_MeV = gate.g4_units.MeV
    g4_volt = gate.g4_units.volt
    g4_eplus = gate.g4_units.eplus

    # World definition
    world = sim.world
    world.size = [1 * g4_m, 1 * g4_m, 1 * g4_m]
    world.material = "G4_Galactic"

    # Field box definition
    box = sim.add_volume("BoxVolume", "field_box")
    box.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
    box.material = "G4_Galactic"

    # --> Define a custom uniform magnetic field along the Y axis
    By = 5 * g4_tesla

    def custom_uniform_B_field(x, y, z, t):
        return [0, By, 0]

    field = fields.CustomMagneticField(
        name="B_uniform_custom", field_function=custom_uniform_B_field
    )
    box.add_field(field)

    # Monoenergetic proton source definition
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

    # (Ignored) Visualisation commands - can be enabled for debugging
    sim.visu_commands += [
        "/tracking/storeTrajectory 2",
        "/vis/scene/add/trajectories smooth",
        "/vis/scene/add/magneticField 10 fullArrow",
        "/vis/scene/add/electricField 10 fullArrow",
    ]

    # Add phase space actor
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = box.name
    phsp.attributes = [
        "PostKineticEnergy",
        "PostPosition",
    ]
    phsp.output_filename = "./test-fields/out/testBBB_phsp.root"
    phsp.steps_to_store = "exiting"
    phsp.root_output.write_to_disk = True

    # Run the simulation
    sim.run()

    # Analyze the phase space output
    file = uproot.open("./test-fields/out/testBBB_phsp.root")
    phsp_tree = file["phsp;1"]
    df = phsp_tree.arrays(library="pd")

    # Analytical calculations for a proton in a uniform magnetic field
    mp = 938.27208943 * g4_MeV
    q = 1 * g4_eplus
    B = By
    r = cyclotron_radius(T, B, mp, q)
    print(f"Expected radius of curvature: {r:.3f} mm")

    # Entry point to the field region
    x0 = 0.0 * g4_mm
    y0 = 0.0 * g4_mm
    z0 = -box.size[2] / 2

    # Centre of the circular trajectory in the XZ plane
    cx = x0 - r
    cz = z0

    # * --- Check 1: circular trajectory in XZ plane (B along Y) ─────────────────────────────
    x_exit = df["PostPosition_X"].values
    y_exit = df["PostPosition_Y"].values
    z_exit = df["PostPosition_Z"].values
    r_TOL = 1.0e-3 * g4_mm

    residual = np.sqrt((x_exit - cx) ** 2 + (z_exit - cz) ** 2) - r
    print(f"\nCircle-fit residual: {residual}")

    is_ok_circular = np.all(np.abs(residual) < r_TOL)
    print(f"Circle constraint satisfied within {r_TOL:.3f} mm: {is_ok_circular}")

    # * ── Check 2 : no deflection in y (B is along y) ─────────────────────────────
    print(f"y displacement: {y_exit - y0} mm")

    is_ok_y_deflection = np.all(np.abs(y_exit - y0) < r_TOL)
    print(f"No deflection in y within {r_TOL:.3f} mm: {is_ok_y_deflection}")

    # * ── Check 3 : energy conservation (B does no work) ──────────────────────────
    KE_exit = df["PostKineticEnergy"].values
    KE_in = T
    e_TOL = 0.01 * g4_MeV
    is_ok_energy_cons = np.all(np.abs(KE_exit - KE_in) < e_TOL)
    print(f"ΔKE (should be ~0 MeV): {KE_exit - KE_in}")

    is_ok = is_ok_circular and is_ok_y_deflection and is_ok_energy_cons
    print(f"\nAll checks passed: {is_ok}")

    utility.test_ok(is_ok)
    # * -----------------------------------------------------------

# * ---------------------------------

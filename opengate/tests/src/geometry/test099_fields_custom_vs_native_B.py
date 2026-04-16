#!/usr/bin/env python3
"""
Test 099 — Custom trampoline B field vs native G4 uniform B field.

Places two boxes side-by-side in one simulation: one with the native
G4UniformMagField, the other with a CustomMagneticField returning the
same constant vector. A proton source fires into each box.

Checks that:
    - Exit positions and energies agree within numerical tolerance.

    - Custom result agrees with the analytical cyclotron radius.
"""

import numpy as np
import uproot

import opengate as gate
from opengate.geometry import fields
from opengate.tests import utility

from test099_fields_helpers import (
    g4_m,
    g4_cm,
    g4_mm,
    g4_tesla,
    g4_MeV,
    g4_eplus,
    PROTON_MASS,
    cyclotron_radius,
)

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test099_fields"
    )

    By = 5 * g4_tesla
    T = 10 * g4_MeV

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 42
    sim.output_dir = paths.output

    world = sim.world
    world.size = [3 * g4_m, 1 * g4_m, 1 * g4_m]
    world.material = "G4_Galactic"

    # Box with native field
    box_native = sim.add_volume("BoxVolume", "box_native")
    box_native.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
    box_native.material = "G4_Galactic"
    box_native.translation = [-80 * g4_cm, 0, 0]

    native_field = fields.UniformMagneticField(name="B_native")
    native_field.field_vector = [0, By, 0]
    box_native.add_field(native_field)

    # Box with custom trampoline field
    box_custom = sim.add_volume("BoxVolume", "box_custom")
    box_custom.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
    box_custom.material = "G4_Galactic"
    box_custom.translation = [80 * g4_cm, 0, 0]

    def custom_uniform_B(x, y, z, t):
        return [0, By, 0]

    custom_field = fields.CustomMagneticField(
        name="B_custom", field_function=custom_uniform_B
    )
    box_custom.add_field(custom_field)

    # Source for native box
    src_native = sim.add_source("GenericSource", "src_native")
    src_native.particle = "proton"
    src_native.n = 1
    src_native.energy.type = "mono"
    src_native.energy.mono = T
    src_native.position.type = "point"
    src_native.position.translation = [-80 * g4_cm, 0, -100 * g4_cm]
    src_native.direction.type = "momentum"
    src_native.direction.momentum = [0, 0, 1]

    # Source for custom box
    src_custom = sim.add_source("GenericSource", "src_custom")
    src_custom.particle = "proton"
    src_custom.n = 1
    src_custom.energy.type = "mono"
    src_custom.energy.mono = T
    src_custom.position.type = "point"
    src_custom.position.translation = [80 * g4_cm, 0, -100 * g4_cm]
    src_custom.direction.type = "momentum"
    src_custom.direction.momentum = [0, 0, 1]

    # Phase space actor for native box
    phsp_native = sim.add_actor("PhaseSpaceActor", "phsp_native")
    phsp_native.attached_to = "box_native"
    phsp_native.attributes = ["PostKineticEnergy", "PostPosition"]
    phsp_native.output_filename = paths.output / "test099_native_B.root"
    phsp_native.steps_to_store = "exiting"

    # Phase space actor for custom box
    phsp_custom = sim.add_actor("PhaseSpaceActor", "phsp_custom")
    phsp_custom.attached_to = "box_custom"
    phsp_custom.attributes = ["PostKineticEnergy", "PostPosition"]
    phsp_custom.output_filename = paths.output / "test099_custom_B.root"
    phsp_custom.steps_to_store = "exiting"

    sim.run()

    # Read results
    df_native = uproot.open(str(paths.output / "test099_native_B.root"))[
        "phsp_native;1"
    ].arrays(library="pd")
    df_custom = uproot.open(str(paths.output / "test099_custom_B.root"))[
        "phsp_custom;1"
    ].arrays(library="pd")

    # Transform to common reference frame (box centres) and compare
    native_x = df_native["PostPosition_X"].values - (-80 * g4_cm)
    custom_x = df_custom["PostPosition_X"].values - (80 * g4_cm)
    native_y = df_native["PostPosition_Y"].values
    custom_y = df_custom["PostPosition_Y"].values
    native_z = df_native["PostPosition_Z"].values
    custom_z = df_custom["PostPosition_Z"].values
    native_KE = df_native["PostKineticEnergy"].values
    custom_KE = df_custom["PostKineticEnergy"].values

    r_TOL = 1e-3 * g4_mm
    e_TOL = 1e-3 * g4_MeV

    # Compare native vs custom
    dx = np.abs(native_x - custom_x)
    dy = np.abs(native_y - custom_y)
    dz = np.abs(native_z - custom_z)
    dKE = np.abs(native_KE - custom_KE)

    is_ok_x = np.all(dx < r_TOL)
    is_ok_y = np.all(dy < r_TOL)
    is_ok_z = np.all(dz < r_TOL)
    is_ok_e = np.all(dKE < e_TOL)

    print(f"dx max: {dx.max():.6f} mm  — OK: {is_ok_x}")
    print(f"dy max: {dy.max():.6f} mm  — OK: {is_ok_y}")
    print(f"dz max: {dz.max():.6f} mm  — OK: {is_ok_z}")
    print(f"dKE max: {dKE.max():.6f} MeV — OK: {is_ok_e}")

    # Compare custom to analytical
    r = cyclotron_radius(T, By, PROTON_MASS, 1 * g4_eplus)
    box_half_z = 250 * g4_mm
    cx, cz = 0.0 - r, -box_half_z
    residual = np.sqrt((custom_x - cx) ** 2 + (custom_z - cz) ** 2) - r
    is_ok_analytical = np.all(np.abs(residual) < r_TOL)
    print(f"Custom vs analytical circle residual: {residual}  — OK: {is_ok_analytical}")

    is_ok = is_ok_x and is_ok_y and is_ok_z and is_ok_e and is_ok_analytical
    utility.test_ok(is_ok)

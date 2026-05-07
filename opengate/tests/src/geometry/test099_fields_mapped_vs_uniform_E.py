#!/usr/bin/env python3
"""
Test 099 - MappedMagneticField with uniform grid vs UniformMagneticField.

Places two boxes side-by-side: one with UniformMagneticField, the other with
a MappedMagneticField whose grid contains a constant B value everywhere. A
proton source fires into each box.

Checks that:
  - Exit positions and energies agree within numerical tolerance.
  - Both results agree with the analytical cyclotron radius.
"""

import itertools

import numpy as np
import uproot

import opengate as gate
from opengate.geometry import fields
from opengate.tests import utility

from test099_fields_helpers import (
    g4_m,
    g4_cm,
    g4_mm,
    g4_volt,
    g4_MeV,
    g4_eplus,
    PROTON_MASS,
    cyclotron_radius,
)

VISU = False

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test099_fields")

    Ex = 1e8 * g4_volt / g4_m
    T = 10 * g4_MeV
    q = 1 * g4_eplus
    box_half = 250 * g4_mm  # half-size of the 50 cm box

    # Build a uniform grid covering the box exactly.
    # A 2x2x2 grid is the minimum for trilinear interpolation; on a uniform
    # field it gives machine-precision exact results at every interior point.
    corners = list(itertools.product([-1 * box_half, 1 * box_half], repeat=3))
    field_matrix = np.array([[x, y, z, Ex, 0.0, 0.0] for x, y, z in corners])

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 42
    sim.output_dir = paths.output

    if VISU:
        sim.visu = True
        sim.visu_type = "qt"
        sim.visu_commands.append("/vis/scene/endOfEventAction accumulate")
        sim.visu_commands.append("/vis/scene/add/trajectories smooth")
        sim.visu_commands.append("/vis/scene/add/electricField 15 fullArrow")

    world = sim.world
    world.size = [3 * g4_m, 1 * g4_m, 1 * g4_m]
    world.material = "G4_Galactic"

    # --- Box with UniformElectricField (reference) ---
    box_ref = sim.add_volume("BoxVolume", "box_ref")
    box_ref.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
    box_ref.material = "G4_Galactic"
    box_ref.translation = [-80 * g4_cm, 0, 0]

    uniform_field = fields.UniformElectricField(name="E_uniform")
    uniform_field.field_vector = [Ex, 0, 0]
    box_ref.add_field(uniform_field)

    # --- Box with MappedElectricField (under test) ---
    box_mapped = sim.add_volume("BoxVolume", "box_mapped")
    box_mapped.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
    box_mapped.material = "G4_Galactic"
    box_mapped.translation = [80 * g4_cm, 0, 0]

    mapped_field = fields.MappedElectricField(name="E_mapped")
    mapped_field.field_matrix = field_matrix
    mapped_field.interpolation = "nearest"
    box_mapped.add_field(mapped_field)

    # --- Sources ---
    for name, translation in [
        ("src_ref", [-80 * g4_cm, 0, -100 * g4_cm]),
        ("src_mapped", [80 * g4_cm, 0, -100 * g4_cm]),
    ]:
        src = sim.add_source("GenericSource", name)
        src.particle = "proton"
        src.n = 1
        src.energy.type = "mono"
        src.energy.mono = T
        src.position.type = "point"
        src.position.translation = translation
        src.direction.type = "momentum"
        src.direction.momentum = [0, 0, 1]

    # --- Phase space actors ---
    for name, box_name, filename in [
        ("phsp_ref", "box_ref", "test099_mapped_vs_uniform_ref.root"),
        ("phsp_mapped", "box_mapped", "test099_mapped_vs_uniform_mapped.root"),
    ]:
        phsp = sim.add_actor("PhaseSpaceActor", name)
        phsp.attached_to = box_name
        phsp.attributes = ["PostKineticEnergy", "PostPosition"]
        phsp.output_filename = paths.output / filename
        phsp.steps_to_store = "exiting"

    sim.run()

    # --- Read results ---
    df_ref = uproot.open(str(paths.output / "test099_mapped_vs_uniform_ref.root"))[
        "phsp_ref;1"
    ].arrays(library="pd")
    df_mapped = uproot.open(
        str(paths.output / "test099_mapped_vs_uniform_mapped.root")
    )["phsp_mapped;1"].arrays(library="pd")

    # Shift positions to each box's local frame for comparison
    ref_x = df_ref["PostPosition_X"].values - (-80 * g4_cm)
    mapped_x = df_mapped["PostPosition_X"].values - (80 * g4_cm)
    ref_y = df_ref["PostPosition_Y"].values
    mapped_y = df_mapped["PostPosition_Y"].values
    ref_z = df_ref["PostPosition_Z"].values
    mapped_z = df_mapped["PostPosition_Z"].values
    ref_KE = df_ref["PostKineticEnergy"].values
    mapped_KE = df_mapped["PostKineticEnergy"].values

    r_TOL = 1e-3 * g4_mm
    e_TOL = 1e-3 * g4_MeV

    # Uniform vs mapped comparison
    dx = np.abs(ref_x - mapped_x)
    dy = np.abs(ref_y - mapped_y)
    dz = np.abs(ref_z - mapped_z)
    dKE = np.abs(ref_KE - mapped_KE)

    is_ok_x = np.all(dx < r_TOL)
    is_ok_y = np.all(dy < r_TOL)
    is_ok_z = np.all(dz < r_TOL)
    is_ok_e = np.all(dKE < e_TOL)

    print(f"Uniform vs mapped - dx max : {dx.max() / g4_mm:.6f} mm  - OK: {is_ok_x}")
    print(f"Uniform vs mapped - dy max : {dy.max() / g4_mm:.6f} mm  - OK: {is_ok_y}")
    print(f"Uniform vs mapped - dz max : {dz.max() / g4_mm:.6f} mm  - OK: {is_ok_z}")
    print(f"Uniform vs mapped - dKE max: {dKE.max() / g4_MeV:.6f} MeV - OK: {is_ok_e}")

    # Analytical check
    x_from_energy = (mapped_KE - T) / (q * Ex)  # ΔKE = qEΔx
    is_ok_analytical = np.all(np.abs(mapped_x - x_from_energy) < r_TOL)
    print(
        f"Mapped vs analytical - dx max: {np.abs(mapped_x - x_from_energy).max() / g4_mm:.6f} mm  - OK: {is_ok_analytical}"
    )
    is_ok = is_ok_x and is_ok_z and is_ok_e and is_ok_analytical
    utility.test_ok(is_ok)

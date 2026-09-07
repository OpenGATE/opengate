#!/usr/bin/env python3
"""
Test 099 - field frame inside a daughter volume.

A field manager is attached to its logical volume with forceToAllDaughters, so
a track inside a field-less daughter of the field volume is still steered by the field.
The field must then be evaluated in the frame of the *field volume*, not in the
frame of the field-less daughter the track happens to be in.

Two boxes carry the same UniformMagneticField with B along local +Y (3 T), and
both are rotated 90 deg about Z so that the local frame differs from the world
frame:

  box_ref  is empty.
  box_dau  contains a daughter without any field that fills it and is itself rotated 45 deg about
           Z relative to its mother.

Checks:
  - box_ref deflects in -Y (B_world along -X), no X deflection
  - box_dau gives the same deflection as box_ref

If the daughter's frame were used instead of the field volume's, the extra
45 deg would rotate B_world and split the deflection between X and Y.
"""

import numpy as np
import uproot
from scipy.spatial.transform import Rotation

import opengate as gate
from opengate.geometry import fields
from opengate.tests import utility

from test099_fields_helpers import (
    g4_mm,
    g4_MeV,
    g4_tesla,
    g4_eplus,
    PROTON_MASS,
    magnetic_deflection,
)

BOX_SIZE = 100 * g4_mm
By = 3 * g4_tesla
KE = 10 * g4_MeV
SEP = 300 * g4_mm

EXPECTED_DEFLECTION = magnetic_deflection(KE, By, PROTON_MASS, 1 * g4_eplus, BOX_SIZE)
TOL_DEFLECTED = 0.01 * g4_mm  # deflected axis must stay within this of expected
TOL_ZERO = 0.01 * g4_mm  # non-deflected axis must stay within this

VISU = False  # set True for interactive qt viewer


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test099_fields")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 99002
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    if VISU:
        sim.visu = True
        sim.visu_type = "qt"
        sim.visu_commands.append("/vis/scene/endOfEventAction accumulate")
        sim.visu_commands.append("/vis/scene/add/trajectories smooth")
        sim.visu_commands.append("/vis/scene/add/magneticField 20 fullArrow")

    m = gate.g4_units.m
    sim.world.size = [2 * m, 2 * m, 2 * m]
    sim.world.material = "G4_Galactic"

    # box_ref: empty reference, rotated 90 deg about Z
    box_ref = sim.add_volume("Box", "box_ref")
    box_ref.size = [BOX_SIZE, BOX_SIZE, BOX_SIZE]
    box_ref.material = "G4_Galactic"
    box_ref.translation = [-SEP, 0, 0]
    box_ref.rotation = Rotation.from_euler("z", 90, degrees=True).as_matrix()

    # box_dau: same placement, but the proton crosses a daughter instead
    box_dau = sim.add_volume("Box", "box_dau")
    box_dau.size = [BOX_SIZE, BOX_SIZE, BOX_SIZE]
    box_dau.material = "G4_Galactic"
    box_dau.translation = [+SEP, 0, 0]
    box_dau.rotation = Rotation.from_euler("z", 90, degrees=True).as_matrix()

    # daughter rotated 45 deg about Z w.r.t. its mother
    inner = sim.add_volume("Box", "inner")
    inner.mother = "box_dau"
    inner.size = [BOX_SIZE / 2, BOX_SIZE / 2, BOX_SIZE]
    inner.material = "G4_Galactic"
    inner.rotation = Rotation.from_euler("z", 45, degrees=True).as_matrix()

    # Same field on both boxes: B along local +Y
    field = fields.UniformMagneticField(name="B_shared")
    field.field_vector = [0, By, 0]
    box_ref.add_field(field)
    box_dau.add_field(field)

    for name, x in (("ref", -SEP), ("dau", +SEP)):
        src = sim.add_source("GenericSource", f"src_{name}")
        src.particle = "proton"
        src.number_of_primaries = 1
        src.energy.type = "mono"
        src.energy.mono = KE
        src.position.type = "point"
        src.position.translation = [x, 0, -300 * g4_mm]
        src.direction.type = "momentum"
        src.direction.momentum = [0, 0, 1]

        phsp = sim.add_actor("PhaseSpaceActor", f"phsp_{name}")
        phsp.attached_to = f"box_{name}"
        phsp.attributes = ["PostPosition"]
        phsp.output_filename = f"phsp_daughter_{name}.root"
        phsp.steps_to_store = "exiting"
        phsp.root_output.write_to_disk = True

    sim.run()

    df_ref = uproot.open(str(paths.output / "phsp_daughter_ref.root"))[
        "phsp_ref;1"
    ].arrays(library="pd")
    df_dau = uproot.open(str(paths.output / "phsp_daughter_dau.root"))[
        "phsp_dau;1"
    ].arrays(library="pd")

    row_ref = df_ref.sort_values("PostPosition_Z").iloc[-1]
    row_dau = df_dau.sort_values("PostPosition_Z").iloc[-1]

    x_ref = row_ref["PostPosition_X"] - (-SEP)
    y_ref = row_ref["PostPosition_Y"]
    x_dau = row_dau["PostPosition_X"] - (+SEP)
    y_dau = row_dau["PostPosition_Y"]

    print(
        f"Analytical expected deflection: {-EXPECTED_DEFLECTION:.2f} mm  (threshold: {TOL_DEFLECTED:.2f} mm)"
    )
    print(f"box_ref (empty):        X={x_ref:.2f} mm  Y={y_ref:.2f} mm")
    print(f"box_dau (R_z 45 daughter): X={x_dau:.2f} mm  Y={y_dau:.2f} mm")

    ok_ref = (
        np.abs(y_ref + EXPECTED_DEFLECTION) < TOL_DEFLECTED and abs(x_ref) < TOL_ZERO
    )
    ok_dau = (
        np.abs(y_dau + EXPECTED_DEFLECTION) < TOL_DEFLECTED and abs(x_dau) < TOL_ZERO
    )
    ok_same = np.abs(y_ref - y_dau) < TOL_DEFLECTED and np.abs(x_ref - x_dau) < TOL_ZERO

    print(f"\nbox_ref deflects in -Y: {ok_ref}")
    print(f"box_dau deflects in -Y (field volume frame, not daughter): {ok_dau}")
    print(f"box_dau matches box_ref: {ok_same}")

    utility.test_ok(ok_ref and ok_dau and ok_same)

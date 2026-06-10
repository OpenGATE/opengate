#!/usr/bin/env python3
"""
Test 099 - MappedMagneticField direction follows volume rotation.

Same scenario as test099_fields_rotated_volume, but the shared field is a
MappedMagneticField.
"""

import itertools

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
TOL_DEFLECTED = 0.01 * g4_mm
TOL_ZERO = 0.01 * g4_mm

VISU = False


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test099_fields")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 42
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

    box_a = sim.add_volume("Box", "box_a")
    box_a.size = [BOX_SIZE, BOX_SIZE, BOX_SIZE]
    box_a.material = "G4_Galactic"
    box_a.translation = [-SEP, 0, 0]

    box_b = sim.add_volume("Box", "box_b")
    box_b.size = [BOX_SIZE, BOX_SIZE, BOX_SIZE]
    box_b.material = "G4_Galactic"
    box_b.translation = [+SEP, 0, 0]
    box_b.rotation = Rotation.from_euler("z", 90, degrees=True).as_matrix()

    half = BOX_SIZE / 2
    corners = list(itertools.product([-half, half], repeat=3))
    field_matrix = np.array([[x, y, z, 0.0, By, 0.0] for x, y, z in corners])

    field = fields.MappedMagneticField(name="B_mapped")
    field.field_matrix = field_matrix
    field.interpolation = "trilinear"
    box_a.add_field(field)
    box_b.add_field(field)

    src_a = sim.add_source("GenericSource", "src_a")
    src_a.particle = "proton"
    src_a.n = 1
    src_a.energy.type = "mono"
    src_a.energy.mono = KE
    src_a.position.type = "point"
    src_a.position.translation = [-SEP, 0, -300 * g4_mm]
    src_a.direction.type = "momentum"
    src_a.direction.momentum = [0, 0, 1]

    src_b = sim.add_source("GenericSource", "src_b")
    src_b.particle = "proton"
    src_b.n = 1
    src_b.energy.type = "mono"
    src_b.energy.mono = KE
    src_b.position.type = "point"
    src_b.position.translation = [+SEP, 0, -300 * g4_mm]
    src_b.direction.type = "momentum"
    src_b.direction.momentum = [0, 0, 1]

    phsp_a = sim.add_actor("PhaseSpaceActor", "phsp_a")
    phsp_a.attached_to = "box_a"
    phsp_a.attributes = ["PostPosition"]
    phsp_a.output_filename = "phsp_mapped_rotated_a.root"
    phsp_a.steps_to_store = "exiting"
    phsp_a.root_output.write_to_disk = True

    phsp_b = sim.add_actor("PhaseSpaceActor", "phsp_b")
    phsp_b.attached_to = "box_b"
    phsp_b.attributes = ["PostPosition"]
    phsp_b.output_filename = "phsp_mapped_rotated_b.root"
    phsp_b.steps_to_store = "exiting"
    phsp_b.root_output.write_to_disk = True

    sim.run()

    df_a = uproot.open(str(paths.output / "phsp_mapped_rotated_a.root"))[
        "phsp_a;1"
    ].arrays(library="pd")
    df_b = uproot.open(str(paths.output / "phsp_mapped_rotated_b.root"))[
        "phsp_b;1"
    ].arrays(library="pd")

    row_a = df_a.sort_values("PostPosition_Z").iloc[-1]
    row_b = df_b.sort_values("PostPosition_Z").iloc[-1]

    xa = row_a["PostPosition_X"] - (-SEP)
    ya = row_a["PostPosition_Y"]
    xb = row_b["PostPosition_X"] - (+SEP)
    yb = row_b["PostPosition_Y"]

    print(
        f"Analytical expected deflection: {-EXPECTED_DEFLECTION:.2f} mm  (threshold: {TOL_DEFLECTED:.2f} mm)"
    )
    print(f"box_a (unrotated): X={xa:.2f} mm  Y={ya:.2f} mm")
    print(f"box_b (R_z 90°):   X={xb:.2f} mm  Y={yb:.2f} mm")

    ok_a_x = np.abs(xa + EXPECTED_DEFLECTION) < TOL_DEFLECTED
    ok_a_y = np.abs(ya) < TOL_ZERO
    print(
        f"box_a deflects in -X: {ok_a_x}  (|{xa:.2f} - {-EXPECTED_DEFLECTION:.2f}| < {TOL_DEFLECTED:.2f})"
    )
    print(f"box_a no Y deflection: {ok_a_y}  ({ya:.2f} mm)")

    ok_b_y = np.abs(yb + EXPECTED_DEFLECTION) < TOL_DEFLECTED
    ok_b_x = np.abs(xb) < TOL_ZERO
    print(
        f"box_b deflects in -Y: {ok_b_y}  (|{yb:.2f} - {-EXPECTED_DEFLECTION:.2f}| < {TOL_DEFLECTED:.2f})"
    )
    print(f"box_b no X deflection: {ok_b_x}  ({xb:.2f} mm)")

    ok_symmetry = np.abs(xa - yb) < TOL_DEFLECTED
    print(f"box_a deflection in -X is similar to box_b deflection in -Y: {ok_symmetry}")

    is_ok = ok_a_x and ok_a_y and ok_b_y and ok_b_x and ok_symmetry
    utility.test_ok(is_ok)

#!/usr/bin/env python3
"""
Test 099 - MappedMagneticField attached to two volumes, dynamic geometry between runs.

Same scenario as test099_fields_multi_volume_refresh, but the shared field is a
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

g4_s = gate.g4_units.s

BOX_SIZE = 100 * g4_mm
SEP = 200 * g4_mm
By = 3 * g4_tesla
KE = 10 * g4_MeV

EXPECTED_DEFLECTION = magnetic_deflection(KE, By, PROTON_MASS, 1 * g4_eplus, BOX_SIZE)
TOL_DEFLECTED = 0.01 * g4_mm
TOL_ZERO = 0.01 * g4_mm

VISU = False


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test099_fields")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 99001
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    if VISU:
        sim.visu = True
        sim.visu_type = "qt"
        sim.visu_commands.append("/vis/scene/endOfEventAction accumulate")
        sim.visu_commands.append("/vis/scene/add/trajectories smooth")
        sim.visu_commands.append("/vis/scene/add/magneticField 20 fullArrow")

    sim.run_timing_intervals = [
        [0, 0.5 * g4_s],
        [0.5 * g4_s, 1.0 * g4_s],
    ]

    sim.world.size = [1 * gate.g4_units.m, 1 * gate.g4_units.m, 1 * gate.g4_units.m]
    sim.world.material = "G4_Galactic"

    box1 = sim.add_volume("Box", "box1")
    box1.size = [BOX_SIZE, BOX_SIZE, BOX_SIZE]
    box1.material = "G4_Galactic"
    box1.translation = [-SEP, 0, 0]
    box1.add_dynamic_parametrisation(
        rotation=[
            Rotation.from_euler("z", 0, degrees=True).as_matrix(),
            Rotation.from_euler("z", 90, degrees=True).as_matrix(),
        ]
    )

    box2 = sim.add_volume("Box", "box2")
    box2.size = [BOX_SIZE, BOX_SIZE, BOX_SIZE]
    box2.material = "G4_Galactic"
    box2.translation = [+SEP, 0, 0]

    half = BOX_SIZE / 2
    corners = list(itertools.product([-half, half], repeat=3))
    field_matrix = np.array([[x, y, z, 0.0, By, 0.0] for x, y, z in corners])

    field = fields.MappedMagneticField(name="B_mapped")
    field.field_matrix = field_matrix
    field.interpolation = "trilinear"
    box1.add_field(field)
    box2.add_field(field)

    src1 = sim.add_source("GenericSource", "src_box1")
    src1.particle = "proton"
    src1.n = [1, 1]
    src1.energy.type = "mono"
    src1.energy.mono = KE
    src1.position.type = "point"
    src1.position.translation = [-SEP, 0, -300 * g4_mm]
    src1.direction.type = "momentum"
    src1.direction.momentum = [0, 0, 1]

    src2 = sim.add_source("GenericSource", "src_box2")
    src2.particle = "proton"
    src2.n = [1, 1]
    src2.energy.type = "mono"
    src2.energy.mono = KE
    src2.position.type = "point"
    src2.position.translation = [+SEP, 0, -300 * g4_mm]
    src2.direction.type = "momentum"
    src2.direction.momentum = [0, 0, 1]

    phsp1 = sim.add_actor("PhaseSpaceActor", "phsp_box1")
    phsp1.attached_to = "box1"
    phsp1.attributes = ["PostPosition", "RunID"]
    phsp1.output_filename = "phsp_mapped_refresh_box1.root"
    phsp1.steps_to_store = "exiting"
    phsp1.root_output.write_to_disk = True

    phsp2 = sim.add_actor("PhaseSpaceActor", "phsp_box2")
    phsp2.attached_to = "box2"
    phsp2.attributes = ["PostPosition", "RunID"]
    phsp2.output_filename = "phsp_mapped_refresh_box2.root"
    phsp2.steps_to_store = "exiting"
    phsp2.root_output.write_to_disk = True

    sim.run()

    df1 = uproot.open(str(paths.output / "phsp_mapped_refresh_box1.root"))[
        "phsp_box1;1"
    ].arrays(library="pd")
    df2 = uproot.open(str(paths.output / "phsp_mapped_refresh_box2.root"))[
        "phsp_box2;1"
    ].arrays(library="pd")

    r0b1 = df1[df1["RunID"] == 0].iloc[0]
    r1b1 = df1[df1["RunID"] == 1].iloc[0]
    r0b2 = df2[df2["RunID"] == 0].iloc[0]
    r1b2 = df2[df2["RunID"] == 1].iloc[0]

    x1_r0 = r0b1["PostPosition_X"] - (-SEP)
    x1_r1 = r1b1["PostPosition_X"] - (-SEP)
    y1_r0 = r0b1["PostPosition_Y"]
    y1_r1 = r1b1["PostPosition_Y"]

    x2_r0 = r0b2["PostPosition_X"] - (+SEP)
    x2_r1 = r1b2["PostPosition_X"] - (+SEP)
    y2_r0 = r0b2["PostPosition_Y"]
    y2_r1 = r1b2["PostPosition_Y"]

    print(
        f"Analytical expected deflection: {EXPECTED_DEFLECTION:.2f} mm  (threshold: {TOL_DEFLECTED:.2f} mm)"
    )
    print(f"box1 run0: ΔX={x1_r0:.2f}  Y={y1_r0:.2f} mm")
    print(f"box1 run1: ΔX={x1_r1:.2f}  Y={y1_r1:.2f} mm")
    print(f"box2 run0: ΔX={x2_r0:.2f}  Y={y2_r0:.2f} mm")
    print(f"box2 run1: ΔX={x2_r1:.2f}  Y={y2_r1:.2f} mm")

    ok_r0b1 = (
        np.abs(x1_r0 + EXPECTED_DEFLECTION) < TOL_DEFLECTED and abs(y1_r0) < TOL_ZERO
    )
    ok_r0b2 = (
        np.abs(x2_r0 + EXPECTED_DEFLECTION) < TOL_DEFLECTED and abs(y2_r0) < TOL_ZERO
    )
    ok_r1b2 = (
        np.abs(x2_r1 + EXPECTED_DEFLECTION) < TOL_DEFLECTED and abs(y2_r1) < TOL_ZERO
    )
    ok_r1b1 = (
        np.abs(y1_r1 + EXPECTED_DEFLECTION) < TOL_DEFLECTED and abs(x1_r1) < TOL_ZERO
    )

    print(f"\nbox1 run0 deflects in -X: {ok_r0b1}")
    print(f"box2 run0 deflects in -X: {ok_r0b2}")
    print(f"box2 run1 deflects in -X (unchanged): {ok_r1b2}")
    print(f"box1 run1 deflects in -Y (verifies refresh): {ok_r1b1}")

    is_ok = ok_r0b1 and ok_r0b2 and ok_r1b2 and ok_r1b1
    utility.test_ok(is_ok)

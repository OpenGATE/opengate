#!/usr/bin/env python3
"""
Test 099 - Stepper selection: all implemented steppers with a uniform B field.

Places one box per stepper side-by-side in a single simulation, each with the
same uniform magnetic field. A proton source fires into each box.

Covers all general-purpose and magnetic-only steppers (NystromRK4,
ExactHelixStepper). Checks that:
  - Every stepper agrees with the analytical cyclotron radius.
  - Every stepper agrees with DormandPrince745 (the reference) in exit
    position and kinetic energy.

See test099_fields_stepper_em.py for non-pure-B field coverage and
magnetic-only stepper guard tests.
"""

import numpy as np
import uproot

import opengate as gate
from opengate.geometry import fields
from opengate.tests import utility

from opengate.tests.src.geometry.test099_fields_helpers import (
    g4_m,
    g4_cm,
    g4_mm,
    g4_tesla,
    g4_MeV,
    g4_eplus,
    PROTON_MASS,
    cyclotron_radius,
)

REF_STEPPER = "DormandPrince745"
ALL_STEPPERS = list(fields._stepper_map.keys())

VISU = False

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test099_fields")

    By = 5 * g4_tesla
    T = 10 * g4_MeV

    n = len(ALL_STEPPERS)
    spacing = 80 * g4_cm

    x_positions = [(i - n // 2) * spacing for i in range(n)]

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
        sim.visu_commands.append("/vis/scene/add/magneticField 20 fullArrow")

    world = sim.world
    world.size = [(n + 1) * spacing, 1 * g4_m, 1 * g4_m]
    world.material = "G4_Galactic"

    for stepper_name, x in zip(ALL_STEPPERS, x_positions):
        box = sim.add_volume("BoxVolume", f"box_{stepper_name}")
        box.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
        box.translation = [x, 0, 0]
        box.material = "G4_Galactic"

        field = fields.UniformMagneticField(name=f"B_{stepper_name}")
        field.field_vector = [0, By, 0]
        field.stepper = stepper_name
        box.add_field(field)

        src = sim.add_source("GenericSource", f"src_{stepper_name}")
        src.particle = "proton"
        src.n = 1
        src.energy.type = "mono"
        src.energy.mono = T
        src.position.type = "point"
        src.position.translation = [x, 0, -100 * g4_cm]
        src.direction.type = "momentum"
        src.direction.momentum = [0, 0, 1]

        phsp = sim.add_actor("PhaseSpaceActor", f"phsp_{stepper_name}")
        phsp.attached_to = f"box_{stepper_name}"
        phsp.attributes = ["PostKineticEnergy", "PostPosition"]
        phsp.output_filename = paths.output / f"test099_stepper_{stepper_name}.root"
        phsp.steps_to_store = "exiting"

    sim.run()

    # --- Collect results ---
    results = {}
    for stepper_name, x in zip(ALL_STEPPERS, x_positions):
        df = uproot.open(str(paths.output / f"test099_stepper_{stepper_name}.root"))[
            f"phsp_{stepper_name};1"
        ].arrays(library="pd")
        results[stepper_name] = (
            df["PostPosition_X"].values - x,  # shift to box-local frame
            df["PostPosition_Z"].values,
            df["PostKineticEnergy"].values,
        )

    # --- Analytical reference ---
    r = cyclotron_radius(T, By, PROTON_MASS, 1 * g4_eplus)
    box_half_z = 250 * g4_mm
    cx, cz = 0.0 - r, -box_half_z

    r_TOL = 1e-2 * g4_mm
    e_TOL = 1e-2 * g4_MeV

    is_ok = True

    # Each stepper vs. analytical
    for stepper_name, (pos_x, pos_z, KE) in results.items():
        residual = np.sqrt((pos_x - cx) ** 2 + (pos_z - cz) ** 2) - r
        ok_pos = bool(np.all(np.abs(residual) < r_TOL))
        ok_e = bool(np.all(np.abs(KE - T) < e_TOL))
        print(
            f"{stepper_name:25s} vs analytical: "
            f"residual={residual[0] / g4_mm:.6f} mm  "
            f"OK_pos={ok_pos}  OK_E={ok_e}"
        )
        is_ok = is_ok and ok_pos and ok_e

    # Each stepper vs. reference (DormandPrince745)
    ref_x, ref_z, ref_KE = results[REF_STEPPER]
    for stepper_name, (pos_x, pos_z, KE) in results.items():
        if stepper_name == REF_STEPPER:
            continue
        dx = np.abs(pos_x - ref_x).max()
        dz = np.abs(pos_z - ref_z).max()
        dKE = np.abs(KE - ref_KE).max()
        ok_cross = bool(dx < r_TOL and dz < r_TOL and dKE < e_TOL)
        print(
            f"{stepper_name:25s} vs {REF_STEPPER}: "
            f"dx={dx / g4_mm:.6f} mm  dz={dz / g4_mm:.6f} mm  "
            f"dKE={dKE:.6f} MeV  OK={ok_cross}"
        )
        is_ok = is_ok and ok_cross

    utility.test_ok(is_ok)

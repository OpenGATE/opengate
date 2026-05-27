#!/usr/bin/env python3
"""
Test 099 - Stepper selection with non-pure-B fields.

Test 1  All general-purpose steppers with a uniform transverse electric field
        (Ex along X). All steppers must agree with each other in exit position
        and kinetic energy (cross-stepper consistency). Physical correctness of
        the field implementation is validated separately in test099_fields_analytical_E.

Test 2  Magnetic-only steppers (NystromRK4, ExactHelixStepper) paired with
        UniformElectricField or UniformElectroMagneticField must raise a
        ValueError.
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
    g4_MeV,
    g4_volt,
    g4_tesla,
    PROTON_MASS,
)

GENERAL_PURPOSE = [
    s for s in fields._stepper_map if s not in fields._magnetic_only_steppers
]
MAGNETIC_ONLY = sorted(fields._magnetic_only_steppers)
REF_STEPPER = "DormandPrince745"

VISU = True

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test099_fields")

    T = 100 * g4_MeV
    L = 500 * g4_mm
    Ex = 1e6 * g4_volt / g4_cm
    By = 3 * g4_tesla

    # Test 1: all general-purpose steppers with transverse E field
    n = len(GENERAL_PURPOSE)
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
        sim.visu_commands.append("/vis/scene/add/electricField 20 fullArrow")

    sim.world.size = [(n + 1) * spacing, 1 * g4_m, 1 * g4_m]
    sim.world.material = "G4_Galactic"

    for stepper_name, x in zip(GENERAL_PURPOSE, x_positions):
        box = sim.add_volume("BoxVolume", f"box_{stepper_name}")
        box.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
        box.translation = [x, 0, 0]
        box.material = "G4_Galactic"

        field = fields.UniformElectricField(name=f"E_{stepper_name}")
        field.field_vector = [Ex, 0, 0]
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
        phsp.output_filename = paths.output / f"test099_stepper_em_{stepper_name}.root"
        phsp.steps_to_store = "exiting"

    sim.run()

    x_TOL = 0.01 * g4_mm
    e_TOL = 1e-3 * g4_MeV
    is_ok = True
    results = {}

    for stepper_name, x in zip(GENERAL_PURPOSE, x_positions):
        df = uproot.open(str(paths.output / f"test099_stepper_em_{stepper_name}.root"))[
            f"phsp_{stepper_name};1"
        ].arrays(library="pd")
        x_exit = float(df["PostPosition_X"].values[0]) - x
        KE_exit = float(df["PostKineticEnergy"].values[0])
        results[stepper_name] = (x_exit, KE_exit)
        print(
            f"{stepper_name:25s} x={x_exit / g4_mm:.4f} mm  KE={KE_exit / g4_MeV:.4f} MeV"
        )

    ref_x, ref_KE = results[REF_STEPPER]
    for stepper_name, (x_exit, KE_exit) in results.items():
        if stepper_name == REF_STEPPER:
            continue
        dx = abs(x_exit - ref_x)
        dKE = abs(KE_exit - ref_KE)
        ok_cross = dx < x_TOL and dKE < e_TOL
        print(
            f"{stepper_name:25s} vs {REF_STEPPER}: "
            f"dx={dx / g4_mm:.6f} mm  dKE={dKE / g4_MeV:.6f} MeV  OK={ok_cross}"
        )
        is_ok = is_ok and ok_cross

    # Test 2: magnetic-only steppers must raise ValueError with E/EM fields
    guard_cases = [
        ("E only", fields.UniformElectricField, {"field_vector": [0, 0, Ex]}),
        (
            "E + B",
            fields.UniformElectroMagneticField,
            {"field_vector_E": [0, 0, Ex], "field_vector_B": [0, By, 0]},
        ),
    ]

    for stepper_name in MAGNETIC_ONLY:
        for label, FieldClass, field_kwargs in guard_cases:
            fld = FieldClass(name="guard_field")
            for attr, val in field_kwargs.items():
                setattr(fld, attr, val)
            fld.stepper = stepper_name

            try:
                fld._validate_stepper()
                ok_guard = False
            except ValueError as exc:
                ok_guard = "only supports pure magnetic fields" in str(exc)

            print(
                f"{stepper_name:25s} + {label:6s}: "
                f"ValueError raised correctly: {ok_guard}"
            )
            is_ok = is_ok and ok_guard

    utility.test_ok(is_ok)

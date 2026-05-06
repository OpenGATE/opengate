#!/usr/bin/env python3
"""
Test 099 - field on a repeated volume.

Two scenarios run in a single simulation.

  LEFT  (X = -100 mm): single box, depth BOX_SIZE along Z.
  RIGHT (X = +100 mm): N_REPS contiguous slabs, each of depth BOX_SIZE/N_REPS,
                       total depth = BOX_SIZE.

Both scenarios expose the proton to the same total path length through field
so the X-deflection should match the analytical sagitta for BOX_SIZE in all cases.

Checks:
  1. Both deflections match the analytical sagitta within TOL_DEFLECTED.
  2. No Y deflection on either side.
  3. Energy conservation (magnetic field does no work).
"""

import uproot

import opengate as gate
from opengate.geometry import fields
from opengate.geometry.utility import get_grid_repetition
from opengate.tests import utility

from test099_fields_helpers import (
    g4_mm,
    g4_MeV,
    g4_tesla,
    g4_eplus,
    PROTON_MASS,
    magnetic_deflection,
)

BOX_SIZE = 50 * g4_mm
N_REPS = 10
SLAB_SIZE = BOX_SIZE / N_REPS
SPACING = SLAB_SIZE
By = 3 * g4_tesla
KE = 10 * g4_MeV
SEP = 100 * g4_mm

# Analytical sagitta for a proton traversing BOX_SIZE of field.
EXPECTED_DEFLECTION = magnetic_deflection(KE, By, PROTON_MASS, 1 * g4_eplus, BOX_SIZE)

TOL_DEFLECTED = 0.1 * g4_mm  # comparison tolerance
TOL_Y = 0.1 * g4_mm
TOL_E = 0.01 * g4_MeV

VISU = False


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test099_fields")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 12345
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    if VISU:
        sim.visu = True
        sim.visu_type = "qt"
        sim.visu_commands.append("/vis/scene/endOfEventAction accumulate")
        sim.visu_commands.append("/vis/scene/add/trajectories smooth")
        sim.visu_commands.append("/vis/scene/add/magneticField 50 fullArrow")

    m = gate.g4_units.m
    sim.world.size = [2 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    # --- LEFT: single box at X = -SEP ---
    box_single = sim.add_volume("Box", "box_single")
    box_single.size = [BOX_SIZE, BOX_SIZE, BOX_SIZE]
    box_single.material = "G4_Galactic"
    box_single.translation = [-SEP, 0, 0]

    field_single = fields.UniformMagneticField(name="B_single")
    field_single.field_vector = [0, By, 0]
    box_single.add_field(field_single)

    src_single = sim.add_source("GenericSource", "src_single")
    src_single.particle = "proton"
    src_single.n = 1
    src_single.energy.type = "mono"
    src_single.energy.mono = KE
    src_single.position.type = "point"
    src_single.position.translation = [-SEP, 0, -200 * g4_mm]
    src_single.direction.type = "momentum"
    src_single.direction.momentum = [0, 0, 1]

    phsp_single = sim.add_actor("PhaseSpaceActor", "phsp_single")
    phsp_single.attached_to = "box_single"
    phsp_single.attributes = ["PostKineticEnergy", "PostPosition"]
    phsp_single.output_filename = "phsp_single.root"
    phsp_single.steps_to_store = "exiting"
    phsp_single.root_output.write_to_disk = True

    # RIGHT: repeated box (N_REPS placements along Z) at X = +SEP
    translations = get_grid_repetition(
        [1, 1, N_REPS], [0, 0, SPACING], start=[0, 0, -SPACING]
    )
    translations = [[+SEP + t[0], t[1], t[2]] for t in translations]

    box_multi = sim.add_volume("Box", "box_multi")
    box_multi.size = [BOX_SIZE, BOX_SIZE, SLAB_SIZE]
    box_multi.material = "G4_Galactic"
    box_multi.translation = translations

    field_multi = fields.UniformMagneticField(name="B_multi")
    field_multi.field_vector = [0, By, 0]
    box_multi.add_field(field_multi)

    src_multi = sim.add_source("GenericSource", "src_multi")
    src_multi.particle = "proton"
    src_multi.n = 1
    src_multi.energy.type = "mono"
    src_multi.energy.mono = KE
    src_multi.position.type = "point"
    src_multi.position.translation = [+SEP, 0, -200 * g4_mm]
    src_multi.direction.type = "momentum"
    src_multi.direction.momentum = [0, 0, 1]

    phsp_multi = sim.add_actor("PhaseSpaceActor", "phsp_multi")
    phsp_multi.attached_to = "box_multi"
    phsp_multi.attributes = ["PostKineticEnergy", "PostPosition"]
    phsp_multi.output_filename = "phsp_multi.root"
    phsp_multi.steps_to_store = "exiting"
    phsp_multi.root_output.write_to_disk = True

    sim.run()

    # Read results
    df_single = uproot.open(str(paths.output / "phsp_single.root"))[
        "phsp_single;1"
    ].arrays(library="pd")
    df_multi = uproot.open(str(paths.output / "phsp_multi.root"))[
        "phsp_multi;1"
    ].arrays(library="pd")

    row_single = df_single.sort_values("PostPosition_Z").iloc[-1]
    row_multi = df_multi.sort_values("PostPosition_Z").iloc[-1]

    # X position relative to each scenario's X centre
    x_single = row_single["PostPosition_X"] - (-SEP)
    y_single = row_single["PostPosition_Y"]
    ke_single = row_single["PostKineticEnergy"]

    x_multi = row_multi["PostPosition_X"] - (+SEP)
    y_multi = row_multi["PostPosition_Y"]
    ke_multi = row_multi["PostKineticEnergy"]

    print(
        f"Analytical expected deflection: {-EXPECTED_DEFLECTION:.2f} mm  (tolerance: ±{TOL_DEFLECTED:.2f} mm)"
    )
    print(
        f"Single box ({BOX_SIZE:.0f} mm):    ΔX={x_single:.2f} mm  Y={y_single:.2f} mm  KE={ke_single:.4f} MeV"
    )
    print(
        f"{N_REPS}x slabs ({SLAB_SIZE:.1f} mm each): ΔX={x_multi:.2f} mm  Y={y_multi:.2f} mm  KE={ke_multi:.4f} MeV"
    )

    # 1. Both deflections match the analytical sagitta.
    ok_single = abs(x_single + EXPECTED_DEFLECTION) < TOL_DEFLECTED
    ok_multi = abs(x_multi + EXPECTED_DEFLECTION) < TOL_DEFLECTED
    print(
        f"Single box matches analytical: {ok_single}  (|{x_single:.2f} - {-EXPECTED_DEFLECTION:.2f}| < {TOL_DEFLECTED:.2f})"
    )
    print(
        f"{N_REPS}-slabs match analytical:  {ok_multi}  (|{x_multi:.2f} - {-EXPECTED_DEFLECTION:.2f}| < {TOL_DEFLECTED:.2f})"
    )

    # 2. No Y deflection
    ok_y_single = abs(y_single) < TOL_Y
    ok_y_multi = abs(y_multi) < TOL_Y
    print(f"No Y deflection (single): {ok_y_single}  ({y_single:.3f} mm)")
    print(f"No Y deflection (multi):  {ok_y_multi}  ({y_multi:.3f} mm)")

    # 3. Energy conservation
    ok_energy_single = abs(ke_single - KE) < TOL_E
    ok_energy_multi = abs(ke_multi - KE) < TOL_E
    print(
        f"Energy conserved (single): {ok_energy_single}  (dKE={ke_single - KE:.4f} MeV)"
    )
    print(
        f"Energy conserved (multi):  {ok_energy_multi}  (dKE={ke_multi - KE:.4f} MeV)"
    )

    is_ok = (
        ok_single
        and ok_multi
        and ok_y_single
        and ok_y_multi
        and ok_energy_single
        and ok_energy_multi
    )
    utility.test_ok(is_ok)

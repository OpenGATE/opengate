#!/usr/bin/env python3
"""
Test 099 - a field on a volume and a different field on its daughter.

Field managers are attached with forceToAllDaughters=True, which overwrites the
field manager of every daughter. The assignment must therefore go outermost
first, so that a field attached to a deeper volume wins over the one it would
otherwise inherit from its mother, whatever order the user added the fields
in.

Setup (repeated twice, adding the fields in the two possible orders):

    outer  100 mm cube, B = 3 T along +Y --> deflects a +Z proton in -X
    inner   40 mm cube inside outer, B = 3 T along +Z.

A proton fired along +Z through the middle therefore bends differently while it is in
the part of 'outer' that is not 'inner'. Both add orders must give the same
deflection, and it must be smaller than for an 'outer' with no
daughter at all.

Checks:
  - adding the outer field first and adding the inner field first agree exactly
  - the daughter really shields the proton: |dX| is smaller than the reference
  - the daughter does not suppress the deflection entirely
"""

import numpy as np
import uproot

import opengate as gate
from opengate.geometry import fields
from opengate.tests import utility

from test099_fields_helpers import g4_mm, g4_MeV, g4_tesla

OUTER_SIZE = 100 * g4_mm
INNER_SIZE = 40 * g4_mm
B = 3 * g4_tesla
KE = 10 * g4_MeV

VISU = False  # set True for interactive qt viewer


def build(sim, name, x_offset, add_order):
    """Add an 'outer' box at x_offset, optionally with a shielding daughter.

    add_order is 'outer_first', 'inner_first' or 'no_daughter'.
    """
    outer = sim.add_volume("Box", f"outer_{name}")
    outer.size = [OUTER_SIZE, OUTER_SIZE, OUTER_SIZE]
    outer.material = "G4_Galactic"
    outer.translation = [x_offset, 0, 0]

    def add_outer_field():
        f = fields.UniformMagneticField(name=f"B_outer_{name}")
        f.field_vector = [0, B, 0]  # bends a +Z proton in -X
        outer.add_field(f)

    def add_inner_field():
        inner = sim.add_volume("Box", f"inner_{name}")
        inner.mother = outer.name
        inner.size = [INNER_SIZE, INNER_SIZE, INNER_SIZE]
        inner.material = "G4_Galactic"
        f = fields.UniformMagneticField(name=f"B_inner_{name}")
        f.field_vector = [0, 0, B]  # parallel to the momentum -> no force
        inner.add_field(f)

    if add_order == "outer_first":
        add_outer_field()
        add_inner_field()
    elif add_order == "inner_first":
        add_inner_field()
        add_outer_field()
    elif add_order == "no_daughter":
        add_outer_field()
    else:
        raise ValueError(add_order)

    src = sim.add_source("GenericSource", f"src_{name}")
    src.particle = "proton"
    src.number_of_primaries = 1
    src.energy.type = "mono"
    src.energy.mono = KE
    src.position.type = "point"
    src.position.translation = [x_offset, 0, -300 * g4_mm]
    src.direction.type = "momentum"
    src.direction.momentum = [0, 0, 1]

    phsp = sim.add_actor("PhaseSpaceActor", f"phsp_{name}")
    phsp.attached_to = outer.name
    phsp.attributes = ["PostPosition"]
    phsp.output_filename = f"phsp_nested_{name}.root"
    phsp.steps_to_store = "exiting"
    phsp.root_output.write_to_disk = True


def exit_dx(paths, name, x_offset):
    df = uproot.open(str(paths.output / f"phsp_nested_{name}.root"))[
        f"phsp_{name};1"
    ].arrays(library="pd")
    row = df.sort_values("PostPosition_Z").iloc[-1]
    return row["PostPosition_X"] - x_offset


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test099_fields")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 99003
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

    # Three independent arms, laterally separated so the protons do not mix.
    arms = {
        "outerfirst": (-400 * g4_mm, "outer_first"),
        "innerfirst": (0.0, "inner_first"),
        "plain": (+400 * g4_mm, "no_daughter"),
    }
    for name, (x, order) in arms.items():
        build(sim, name, x, order)

    sim.run()

    dx = {name: exit_dx(paths, name, x) for name, (x, _) in arms.items()}

    print(f"outer field added first: dX = {dx['outerfirst']:.4f} mm")
    print(f"inner field added first: dX = {dx['innerfirst']:.4f} mm")
    print(f"no daughter (reference): dX = {dx['plain']:.4f} mm")

    is_ok = True

    # The result must not depend on the order the fields were added.
    # Same geometry, same seed, identical result to floating point noise.
    is_ok = (
        utility.print_test(
            np.isclose(dx["outerfirst"], dx["innerfirst"], atol=1e-3 * g4_mm),
            f"Add order does not change the result "
            f"({dx['outerfirst']:.6f} vs {dx['innerfirst']:.6f} mm)",
        )
        and is_ok
    )

    # The daughter's own field exerts a different force.
    # If the daughter's field were clobbered by the mother's, the bendings would be equal.
    is_ok = (
        utility.print_test(
            abs(dx["outerfirst"]) < abs(dx["plain"]) - 0.1 * g4_mm,
            f"Daughter field is in effect: |dX| {abs(dx['outerfirst']):.4f} mm "
            f"< reference {abs(dx['plain']):.4f} mm",
        )
        and is_ok
    )

    # ... but the mother still bends the proton outside the daughter.
    is_ok = (
        utility.print_test(
            abs(dx["outerfirst"]) > 0.1 * g4_mm,
            f"Mother field still acts outside the daughter: "
            f"|dX| = {abs(dx['outerfirst']):.4f} mm",
        )
        and is_ok
    )

    utility.test_ok(is_ok)

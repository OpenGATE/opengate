#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Filter on one component of a 3-vector attribute (issue #1049):
F.PostPosition_X < 0 * mm, and the same with _Y, _Z and other 3-vector
attributes (e.g. PreDirection).

All phase spaces see the same steps: each filtered phase space must contain
exactly the steps of the phase space without filter that fulfil the condition.
"""

import numpy as np
import uproot
import opengate as gate
from opengate.tests import utility
from opengate.actors.filters import GateFilterBuilder

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    sim = gate.Simulation()
    sim.random_seed = 42
    sim.output_dir = paths.output

    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV

    box = sim.add_volume("Box", "box")
    box.size = [10 * cm, 10 * cm, 10 * cm]
    box.material = "G4_WATER"

    # a wide beam, so that half of the particles are at x < 0
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 1 * MeV
    source.position.type = "box"
    source.position.size = [6 * cm, 6 * cm, 1 * mm]
    source.position.translation = [0, 0, -20 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = 2000

    F = GateFilterBuilder()
    filters = {
        "no_filter": None,
        "x_lt_0": F.PostPosition_X < 0 * mm,
        "x_ge_0": F.PostPosition_X >= 0,
        "x_lt_0_and_y_gt_1cm": (F.PostPosition_X < 0) & (F.PostPosition_Y > 1 * cm),
        "dir_z_lt_0.9": F.PreDirection_Z < 0.9,
        "not_x_lt_0": ~(F.PostPosition_X < 0),
    }
    for name, f in filters.items():
        ps = sim.add_actor("PhaseSpaceActor", f"ps_{name}")
        ps.attached_to = box
        ps.steps_to_store = "all"
        ps.attributes = ["PostPosition", "PreDirection", "TrackID"]
        ps.output_filename = f"test023_vector_component_{name}.root"
        if f is not None:
            ps.filter = f

    sim.run()

    def read(name):
        ps = sim.get_actor(f"ps_{name}")
        return uproot.open(ps.get_output_path())[ps.name].arrays(library="np")

    data = {name: read(name) for name in filters}
    ref = data["no_filter"]
    x = ref["PostPosition_X"]
    y = ref["PostPosition_Y"]
    dz = ref["PreDirection_Z"]
    expected = {
        "x_lt_0": x < 0,
        "x_ge_0": x >= 0,
        "x_lt_0_and_y_gt_1cm": (x < 0) & (y > 1 * cm),
        "dir_z_lt_0.9": dz < 0.9,
        "not_x_lt_0": ~(x < 0),
    }

    is_ok = utility.print_test(
        (x < 0).sum() > 0 and (x >= 0).sum() > 0 and (dz < 0.9).sum() > 0,
        f"Without filter: {len(x)} steps, {(x < 0).sum()} with x < 0, "
        f"{(dz < 0.9).sum()} with direction z < 0.9",
    )
    for name, mask in expected.items():
        d = data[name]
        b = len(d["PostPosition_X"]) == mask.sum()
        for k in ["PostPosition_X", "PostPosition_Y", "PreDirection_Z", "TrackID"]:
            b = b and np.array_equal(np.sort(d[k]), np.sort(ref[k][mask]))
        is_ok = (
            utility.print_test(
                b,
                f"{name:22}: {len(d['PostPosition_X'])} steps "
                f"(expected {mask.sum()})",
            )
            and is_ok
        )

    utility.test_ok(is_ok)

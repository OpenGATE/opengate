#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The type of an attribute filter (double, int, string) must follow the type of
the attribute, not the type of the compared value (issue #658):

- F.TotalEnergyDeposit > 0 (an int value for a double attribute) is the same
  filter as F.TotalEnergyDeposit > 0.0 (it crashed before);
- F.TrackID == 1.0 (a float value for an int attribute) is the same filter as
  F.TrackID == 1 (it crashed before);
- vector attributes, or a non-integral value for an int attribute, give a
  clear error.

The first filter is also the answer to issue #658: do not store the steps
without deposited energy.
"""

import uproot
import opengate as gate
from opengate.tests import utility
from opengate.actors.filters import GateFilterBuilder


def raises_error(f):
    try:
        f()
    except Exception as e:
        print(f"Expected error: {str(e).strip().splitlines()[-1]}")
        return True
    return False


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    sim = gate.Simulation()
    sim.random_seed = 42
    sim.output_dir = paths.output

    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV

    box = sim.add_volume("Box", "box")
    box.size = [10 * cm, 10 * cm, 10 * cm]
    box.material = "G4_WATER"

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 1 * MeV
    source.position.translation = [0, 0, -20 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = 2000

    F = GateFilterBuilder()
    filters = {
        "no_filter": None,
        "edep_int": F.TotalEnergyDeposit > 0,
        "edep_float": F.TotalEnergyDeposit > 0.0,
        "track_int": F.TrackID == 1,
        "track_float": F.TrackID == 1.0,
    }
    for name, f in filters.items():
        ps = sim.add_actor("PhaseSpaceActor", f"ps_{name}")
        ps.attached_to = box
        ps.steps_to_store = "all"
        ps.attributes = ["TotalEnergyDeposit", "TrackID"]
        ps.output_filename = f"test023_attribute_types_{name}.root"
        if f is not None:
            ps.filter = f

    sim.run()

    def read(name):
        ps = sim.get_actor(f"ps_{name}")
        return uproot.open(ps.get_output_path())[ps.name].arrays(library="np")

    data = {name: read(name) for name in filters}
    for name, d in data.items():
        edep = d["TotalEnergyDeposit"]
        print(
            f"{name:12}: {len(edep)} steps, {(edep == 0).sum()} with edep = 0, "
            f"edep {edep.sum():.4f} MeV, TrackID 1: {(d['TrackID'] == 1).sum()}"
        )

    ref = data["no_filter"]
    is_ok = utility.print_test(
        (ref["TotalEnergyDeposit"] == 0).sum() > 0 and (ref["TrackID"] != 1).sum() > 0,
        "Without filter: some steps without edep and some secondaries",
    )

    # edep > 0: same filter with int and float, no step without edep, and the
    # same total edep as without filter
    a, b = (
        data["edep_int"]["TotalEnergyDeposit"],
        data["edep_float"]["TotalEnergyDeposit"],
    )
    is_ok = (
        utility.print_test(
            len(a) == len(b) == (ref["TotalEnergyDeposit"] > 0).sum()
            and (a == 0).sum() == 0
            and abs(a.sum() - ref["TotalEnergyDeposit"].sum()) < 1e-6,
            f"F.TotalEnergyDeposit > 0 (int) and > 0.0: {len(a)} and {len(b)} steps",
        )
        and is_ok
    )

    # TrackID == 1: same filter with int and float
    a, b = data["track_int"]["TrackID"], data["track_float"]["TrackID"]
    is_ok = (
        utility.print_test(
            len(a) == len(b) == (ref["TrackID"] == 1).sum() and (a != 1).sum() == 0,
            f"F.TrackID == 1 and == 1.0: {len(a)} and {len(b)} steps",
        )
        and is_ok
    )

    # clear errors
    is_ok = (
        utility.print_test(
            raises_error(lambda: F.PostPosition > 0),
            "Vector attribute in a filter: error",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            raises_error(lambda: F.TrackID == 1.5),
            "Int attribute compared with 1.5: error",
        )
        and is_ok
    )

    utility.test_ok(is_ok)

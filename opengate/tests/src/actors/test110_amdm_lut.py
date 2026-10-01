#!/usr/bin/env python3
"""Independent expectations for the bound C++ AMDM lookup and validation."""
from pathlib import Path
import numpy as np
import opengate as gate
import opengate_core as g4
from opengate.tests import utility
from opengate.actors.amdmoutput import ActorOutputAMDM
from opengate.actors.doseactors import AMDMActor
from test110_amdm_helpers import output_dir


def lookup_actor(path, bins=2):
    sim = gate.Simulation()
    actor = sim.add_actor("AMDMActor", "lookup")
    actor.AMDM_Bins = bins
    actor.LUTfilename = str(path)
    actor.InitializeUserInfo(actor.user_info)
    return actor


if __name__ == "__main__":
    directory = output_dir("lut")
    assert hasattr(g4, "GateAMDMActor")
    assert AMDMActor.has_been_processed() and ActorOutputAMDM.has_been_processed()
    path = directory / "lookup.txt"
    # Unequal groups and a singleton final charge are valid.
    path.write_text("  # comment\n\n1 1 2 8 .2 .8\n1 3 6 4 .6 .4 # inline\n"
                    "8 .9 3 9 .3 .7\n8 4 7 1 .7 .3\n10 2 11 13 .1 .9\n")
    actor = lookup_actor(path)
    np.testing.assert_array_equal(actor.Lookup(1, 1), [2, 8, .2, .8])
    np.testing.assert_allclose(actor.Lookup(1, 2), [4, 6, .4, .6], rtol=0, atol=1e-15)
    np.testing.assert_array_equal(actor.Lookup(1, .01), [2, 8, .2, .8])
    np.testing.assert_array_equal(actor.Lookup(1, 99), [6, 4, .6, .4])
    for energy in [0, 2, 999, float("inf")]:
        np.testing.assert_array_equal(actor.Lookup(10, energy), [11, 13, .1, .9])
    for charge in [0, 2, 9, 11]:
        assert actor.Lookup(charge, 2) == []
    assert actor.Lookup(1, float("nan")) == []
    malformed = {
        "empty": (" # nothing\n", "no data"),
        "columns": ("1 1 2 8 .2\n", "column count"),
        "negative_charge": ("-1 1 2 8 .2 .8\n", "charge"),
        "fractional_charge": ("1.5 1 2 8 .2 .8\n", "charge"),
        "zero_charge": ("0 1 2 8 .2 .8\n", "charge"),
        "charge_overflow": ("1e20 1 2 8 .2 .8\n", "charge"),
        "zero_energy": ("1 0 2 8 .2 .8\n", "energy"),
        "duplicate": ("1 1 2 8 .2 .8\n1 1 6 4 .6 .4\n", "unique"),
        "descending_energy": ("1 3 2 8 .2 .8\n1 1 6 4 .6 .4\n", "increasing"),
        "descending_charge": ("8 1 2 8 .2 .8\n1 2 6 4 .6 .4\n", "groups"),
        "nan": ("1 1 nan 8 .2 .8\n", "finite"),
        "infinity": ("1 1 2 8 inf .8\n", "finite"),
        "trailing_text": ("1 1 2 8 .2 .8 junk\n", "numeric"),
    }
    for name, (text, message) in malformed.items():
        bad_path = directory / f"{name}.txt"
        bad_path.write_text(text)
        try:
            lookup_actor(bad_path)
        except ValueError as error:
            assert message in str(error), (name, error)
        else:
            raise AssertionError(f"accepted malformed LUT: {name}")
    for bad_path, bins, message in [(directory / "missing.txt", 2, "cannot open"),
                                    (path, 3, "column count"), (path, 0, "positive")]:
        try:
            lookup_actor(bad_path, bins)
        except ValueError as error:
            assert message in str(error), error
        else:
            raise AssertionError((bad_path, bins))
    print("Exact, interpolated, clamped, missing-charge and malformed LUT checks passed")
    utility.test_ok(True)

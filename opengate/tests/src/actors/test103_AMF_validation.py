#!/usr/bin/env python3
"""Configuration defaults, explicit limitations and independent enablement."""

import numpy as np
import opengate as gate

from opengate.tests import utility
from test103_AMF_helpers import make_simulation


def expect_error(call, message):
    """Require the callable to raise an error containing the requested message."""
    try:
        call()
    except Exception as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError(f"Expected failure containing {message}")


def main():
    """Check defaults, configuration errors and unsupported run/job operations."""
    paths = utility.get_default_test_paths(__file__, output_folder="test103_AMF_validation")
    sim, actor, _ = make_simulation(paths.output)
    assert actor.DomainRadius == .3 * gate.g4_units.um
    assert actor.NucleusRadius == 4.5 * gate.g4_units.um
    assert actor.AlphaRef == .217 / gate.g4_units.Gy
    assert actor.AlphaNot == .117 / gate.g4_units.Gy
    assert actor.BetaRef == .0615 / gate.g4_units.Gy**2
    default = sim.add_actor("AMFActor", "defaults")
    assert default.tsed_file_name == "tsed.dat"
    assert default.microdosimetric_spectra_file_name == "microdosimetric_spectra.dat"
    assert default.MicrodosimetricSpectra is True
    assert not default.DoseAveragedLinealEnergy.active
    assert not default.DoseAveragedLinealEnergySaturationCorrected.active
    assert default.Alpha_MCFMKM.active and default.Beta_MCFMKM.active
    actor.check_user_input()
    for name, value, message in (("DomainRadius", 0, "DomainRadius"),
                                  ("DomainRadius", .6 * gate.g4_units.um, "DomainRadius"),
                                  ("NucleusRadius", 0, "radii"),
                                  ("BetaRef", 0, "BetaRef"),
                                  ("AlphaNot", -1, "alpha"),
                                  ("AlphaRef", np.inf, "finite number"),
                                  ("DomainRadius", "bad", "finite number"),
                                  ("DomainRadius", 1j, "finite number"),
                                  ("MicrodosimetricSpectra", 1, "bool"),
                                  ("size", [1, 1, 0], "positive"),
                                  ("size", [1, 1, 1.5], "integers"),
                                  ("size", [1e100, 1, 1], "too large"),
                                  ("spacing", [1, 0, 1], "positive"),
                                  ("spacing", [1e200, 1e200, 1], "voxel volume"),
                                  ("spacing", [1e-200, 1e-200, 1e-200], "voxel volume"),
                                  ("translation", [1, 2], "three finite"),
                                  ("rotation", np.zeros((3, 3)), "orthogonal"),
                                  ("rotation", np.full((3, 3), "bad"), "orthogonal"),
                                  ("tsed_file_name", str(paths.output / "missing"), "does not exist")):
        old = getattr(actor, name)
        setattr(actor, name, value)
        expect_error(actor.check_user_input, message)
        setattr(actor, name, old)
    old = sim.run_timing_intervals
    sim.run_timing_intervals = [[0, 1], [1, 2]]
    expect_error(actor.check_user_input, "one run interval")
    sim.number_of_threads = 4
    expect_error(actor.check_user_input, "one run interval")
    sim.number_of_threads = 1
    sim.run_timing_intervals = old
    sim.number_of_threads = 2
    actor.check_user_input()
    sim.number_of_threads = 1
    sim.force_multithread_mode = True
    actor.check_user_input()
    sim.force_multithread_mode = False
    expect_error(lambda: actor.user_output.dose.plan_merge(), "merging finalized")
    expect_error(lambda: actor.import_user_output_from_actor(actor, actor), "merging finalized")
    # Exercise the C++ checks independently of Python configuration validation.
    for size, spacing, message in (([1e100, 1, 1], [1, 1, 1], "dimensions"),
                                   ([1e6, 1e6, 1e6], [1, 1, 1], "overflow"),
                                   ([1, 1, 1], [1e200, 1e200, 1], "voxel volume")):
        actor.size, actor.spacing = size, spacing
        actor.InitializeUserInfo(actor.user_info)
        expect_error(actor.InitializeCpp, message)
    utility.test_ok(True)


if __name__ == "__main__":
    main()

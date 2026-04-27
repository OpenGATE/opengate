#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test036_adder_depth_helpers as t036
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test036_adder_depth", "test036"
    )

    # create and run the simulation
    sim = t036.create_simulation("param", paths, "_par")

    # start simulation
    sim.run()

    """
    WARNING
    The reference data for this test was made with Gate 9.x, Geant4 11.2
    Since Geant4 11.4 (January 2026), some physics changed and the hits distributions
    are different from the previous version. The "singles" should not change too much.
    We finally decided to keep the "old" reference data and increase the tolerance as
    the ground truth is not known here.
    """

    # test the output
    is_ok = t036.test_output(sim, paths)

    utility.test_ok(is_ok)

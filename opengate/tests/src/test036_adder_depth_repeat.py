#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test036_adder_depth_helpers as t036
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test036_adder_depth", "test036"
    )

    # create and run the simulation
    sim = t036.create_simulation("repeat", paths)

    # start simulation
    sim.run()

    # test the output
    is_ok = t036.test_output(sim, paths)

    utility.test_ok(is_ok)

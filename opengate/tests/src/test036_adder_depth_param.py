#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test036_adder_depth_helpers as t036

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "gate_test036_adder_depth")

    # create and run the simulation
    sim = t036.create_simulation("param")

    # start simulation
    sim.run()

    # test the output
    is_ok = t036.test_output(sim.output)

    gate.test_ok(is_ok)

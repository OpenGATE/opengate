#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test014_engine_helpers as test014

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test014_1")
    sim = gate.Simulation()
    test014.define_simulation(sim, paths)

    # go
    sim.run(start_new_process=True)

    # get output
    is_ok = test014.test_output(sim)

    utility.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test014_engine_helpers as test014
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    sim = gate.Simulation()
    test014.define_simulation(sim)

    # go with a new process
    sim.run(start_new_process=True)

    # get output
    is_ok = test014.test_output(sim)

    # go without a new process
    sim.run(start_new_process=False)

    # get output
    is_ok = test014.test_output(sim) and is_ok

    utility.test_ok(is_ok)

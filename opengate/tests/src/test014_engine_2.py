#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test014_engine_helpers import *

if __name__ == "__main__":
    sim = gate.Simulation()
    define_simulation(sim)

    # go with a new process
    sim.run(start_new_process=True)

    # get output
    is_ok = test_output(sim.output)

    # go without a new process
    sim.run(start_new_process=False)

    # get output
    is_ok = test_output(sim.output) and is_ok

    gate.test_ok(is_ok)

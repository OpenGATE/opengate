#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test014_engine_helpers import *

if __name__ == "__main__":
    sim = gate.Simulation()
    define_simulation(sim, 3)

    # go with a new process that will use 3 threads
    sim.run(start_new_process=True)

    # get output
    is_ok = test_output(sim.output)

    gate.test_ok(is_ok)

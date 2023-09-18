#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test014_engine_helpers import *

if __name__ == "__main__":
    sim = gate.Simulation()
    define_simulation(sim, 5)

    # go without sub process, but with multithread
    sim.run(start_new_process=False)

    # get output
    is_ok = test_output(sim.output)

    gate.test_ok(is_ok)

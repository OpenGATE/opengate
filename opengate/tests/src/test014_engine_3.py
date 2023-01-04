#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test014_engine_helpers import *

sim = gate.Simulation()
define_simulation(sim, 3)

# go with a new process that will use 3 threads
se = gate.SimulationEngine(sim, start_new_process=True)
output = se.start()

# get output
is_ok = test_output(output)

gate.test_ok(is_ok)

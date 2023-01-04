#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test014_engine_helpers import *

sim = gate.Simulation()
define_simulation(sim)

# go with a new process
se = gate.SimulationEngine(sim, start_new_process=True)
output = se.start()

# get output
is_ok = test_output(output)

# go without a new process
se = gate.SimulationEngine(sim, start_new_process=False)
output = se.start()

# get output
is_ok = test_output(output) and is_ok

gate.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test014_engine_helpers import *

sim = gate.Simulation()
define_simulation(sim, 5)

# go without sub process, but with multithread
se = gate.SimulationEngine(sim, start_new_process=False)
output = se.start()

# get output
is_ok = test_output(output)

gate.test_ok(is_ok)

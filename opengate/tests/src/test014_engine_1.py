#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test014_engine_helpers import *

sim = gate.Simulation()
define_simulation(sim)

# go
sim.run(start_new_process=True)

# get output
is_ok = test_output(sim.output)

gate.test_ok(is_ok)

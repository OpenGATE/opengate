#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test039_hits_memory_check_helpers import *

paths = gate.get_default_test_paths(__file__, "")

# create the simulation
sim = create_simu(8)
ui = sim.user_info
ui.random_seed = "auto"

# go
output = sim.start()

is_ok = test_results(output)

gate.test_ok(is_ok)

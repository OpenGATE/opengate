#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test028_ge_nm670_spect_2_helpers import *

paths = gate.get_default_test_paths(__file__, "gate_test028_ge_nm670_spect")

# create the simulation
sim = gate.Simulation()

# main description
create_spect_simu(sim, paths)

# mono thread
ui = sim.user_info
ui.number_of_threads = 1

output = sim.start()

# check
is_ok = test_spect_hits(output, paths)

gate.test_ok(is_ok)

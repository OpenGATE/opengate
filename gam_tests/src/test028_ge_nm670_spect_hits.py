#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test028_ge_nm670_spect_base import *

paths = gam.get_common_test_paths(__file__, 'gate_test028_ge_nm670_spect')

# create the simulation
sim = gam.Simulation()

# main description
create_spect_simu(sim, paths)

# mono thread
ui = sim.user_info
ui.number_of_threads = 1

sim.initialize()
sim.start()

# check
test_spect_hits(sim, paths)




#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test053_gid_helpers1 import *

"""
Consider a source of ac225 and store all emitted gammas
"""

paths = gate.get_default_test_paths(__file__, "", output="test053")
z = 89
a = 225
sim = gate.Simulation()

ion_name, daughters = create_ion_gamma_simulation(sim, paths, z, a)

# go
# FIXME: need to start new process. something to change in initialize_g4_verbose ?
output = sim.start(start_new_process=True)

#
is_ok = analyse(paths, sim, output, ion_name, z, a, daughters, log_flag=False)

# the test is ok, but energy binning make it looks weird.
# ignore for the moment

gate.test_ok(is_ok)

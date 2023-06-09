#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test053_gid_helpers1 import *

"""
Consider a source of fr221 and store all emitted gammas
"""

paths = gate.get_default_test_paths(__file__, "", output_folder="test053")
z = 87
a = 221
sim = gate.Simulation()

ion_name, daughters = create_ion_gamma_simulation(sim, paths, z, a)

# go
# FIXME: need to start new process. something to change in initialize_g4_verbose ?
output = sim.start(start_new_process=True)

#
is_ok = analyse(paths, sim, output, ion_name, z, a, daughters, log_flag=False, tol=0.08)

gate.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test053_gamma_from_ion_decay_helpers import *

"""
Consider a source of Bi213 and store all emitted gammas
"""

paths = gate.get_default_test_paths(__file__, "", output="test053")
z = 83
a = 213
sim = gate.Simulation()

ion_name, daughters = create_ion_gamma_simulation(sim, paths, z, a)

# go
# FIXME: need to start new process. something to change in initialize_g4_verbose ?
output = sim.start(start_new_process=True)

#
is_ok = analyse(paths, sim, output, ion_name, z, a, daughters, log_flag=False)

gate.test_ok(is_ok)

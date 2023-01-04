#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test033_rotation_spect_aa_helpers import *

paths = gate.get_default_test_paths(__file__, "")

# create the simulation
sim = gate.Simulation()
sources = create_test(sim)

# AA mode
for source in sources:
    source.direction.acceptance_angle.skip_policy = "ZeroEnergy"

# go
output = sim.start()

# check
is_ok = evaluate_test(output, sources, 8, 1968330)

gate.test_ok(is_ok)

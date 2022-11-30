#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect_ge_nm670 as gate_spect
from test033_rotation_spect_aa_base import *

paths = gate.get_default_test_paths(__file__, "")

# create the simulation
sim = gate.Simulation()
sources = create_test(sim, nb_thread=4)

# AA mode
for source in sources:
    source.direction.acceptance_angle.skip_mode = "SkipEvents"

# go
sim.initialize()
sim.start()

# check
is_ok = evaluate_test(sim, sources, 15, 1968330)

gate.test_ok(is_ok)

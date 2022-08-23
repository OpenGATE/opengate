#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect_ge_nm670 as gate_spect
from test028_ge_nm670_spect_base import *

paths = gate.get_default_test_paths(__file__, "gate_test028_ge_nm670_spect")

# create the simulation
sim = gate.Simulation()

# main description
create_spect_simu(sim, paths, 3)

# go
sim.initialize()
sim.start()

# check
test_spect_hits(sim, paths)

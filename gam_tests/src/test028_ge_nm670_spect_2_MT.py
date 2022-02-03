#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_ge_nm670_spect as gam_spect
from test028_ge_nm670_spect_base import *

paths = gam.get_common_test_paths(__file__, 'gate_test028_ge_nm670_spect')

# create the simulation
sim = gam.Simulation()

# main description
create_spect_simu(sim, paths, 3)

# go
sim.initialize()
sim.start()

# check
test_spect_hits(sim, paths)




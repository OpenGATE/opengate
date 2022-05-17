#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import gam_g4 as g4
from scipy.spatial.transform import Rotation
import test036_adder_depth_base as t036
import uproot
import matplotlib.pyplot as plt

paths = gam.get_default_test_paths(__file__, 'gate_test036_adder_depth')

# create and run the simulation
sim = t036.create_simulation('repeat')

# start simulation
sim.start()

# test the output
is_ok = t036.test_output(sim)

gam.test_ok(is_ok)

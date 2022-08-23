#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4
from scipy.spatial.transform import Rotation
import test036_adder_depth_base as t036
import uproot
import matplotlib.pyplot as plt

paths = gate.get_default_test_paths(__file__, "gate_test036_adder_depth")

# create and run the simulation
sim = t036.create_simulation("param")

# start simulation
sim.start()

# test the output
is_ok = t036.test_output(sim)

gate.test_ok(is_ok)

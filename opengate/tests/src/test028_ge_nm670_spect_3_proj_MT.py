#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test028_ge_nm670_spect_2_helpers import *

paths = gate.get_default_test_paths(__file__, "gate_test028_ge_nm670_spect")

# create the simulation
sim = gate.Simulation()

# main description
spect = create_spect_simu(sim, paths, 4)
proj = test_add_proj(sim, paths)

# rotate spect
cm = gate.g4_units("cm")
psd = 6.11 * cm
p = [0, 0, -(20 * cm + psd)]
spect.translation, spect.rotation = gate.get_transform_orbiting(p, "y", -15)

# go
output = sim.start()

# check
proj = output.get_actor("Projection")
test_spect_proj(output, paths, proj)

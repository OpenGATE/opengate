#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test028_ge_nm670_spect_base import *

paths = gam.get_common_test_paths(__file__, 'gate_test028_ge_nm670_spect')

# create the simulation
sim = gam.Simulation()

# main description
spect = create_spect_simu(sim, paths, 1)
proj = test_add_proj(sim, paths)

# rotate spect
cm = gam.g4_units('cm')
psd = 6.11 * cm
p = [0, 0, -(20 * cm + psd)]
spect.translation, spect.rotation = gam.get_transform_orbiting(p, 'y', -15)

sim.initialize()
sim.start()

# check
test_spect_proj(sim, paths, proj)

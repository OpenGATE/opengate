#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test028_ge_nm670_spect_4_acc_angle_helpers import *

# create the simulation
sim = gate.Simulation()

# simu description
spect, proj = create_spect_simu(
    sim,
    paths,
    number_of_threads=1,
    activity_kBq=1000,
    aa_enabled=True,
    aa_mode="ZeroEnergy",
)

# go
print(proj)
output = sim.start(True)
print(proj)

# check
is_ok = compare_result(output, proj, "test028_aa_zero_energy.png", sum_tolerance=17)
gate.test_ok(is_ok)

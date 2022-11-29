#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test028_ge_nm670_spect_acc_angle_base import *

# create the simulation
sim = gate.Simulation()

# simu description
spect, proj = create_spect_simu(
    sim,
    paths,
    number_of_threads=1,
    activity_kBq=1000,
    aa_enabled=True,
    aa_mode="EnergyZero",
)

# go
sim.initialize()
sim.start()

# check
is_ok = compare_result(sim, proj, "test028_aa_energy_zero.png")
gate.test_ok(is_ok)

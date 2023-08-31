#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test028_ge_nm670_spect_4_acc_angle_helpers import *

if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()

    # simu description
    spect, proj = create_spect_simu(
        sim,
        paths,
        number_of_threads=3,
        activity_kBq=1000,
        aa_enabled=True,
        aa_mode="SkipEvents",
    )

    # go
    sim.run()

    # check
    is_ok = compare_result(
        sim.output, proj, "test028_aa_skip_events.png", sum_tolerance=25
    )
    gate.test_ok(is_ok)

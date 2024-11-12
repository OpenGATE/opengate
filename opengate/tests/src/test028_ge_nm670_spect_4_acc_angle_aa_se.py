#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test028_ge_nm670_spect_4_acc_angle_helpers as test028
from opengate.tests import utility

if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()

    # simu description
    spect, proj = test028.create_spect_simu(
        sim,
        test028.paths,
        number_of_threads=1,
        activity_kBq=1000,
        aa_enabled=True,
        aa_mode="SkipEvents",
        version="_4_acc_angle_aa_se",
    )

    # go
    sim.run()

    # check
    is_ok = test028.compare_result(
        sim,
        proj,
        "test028_aa_skip_events.png",
        sum_tolerance=20,
        version="_4_acc_angle_aa_se",
    )
    utility.test_ok(is_ok)

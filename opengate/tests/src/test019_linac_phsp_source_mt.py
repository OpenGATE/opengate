#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import test019_linac_phsp_helpers as test019

if __name__ == "__main__":
    # create sim
    sim = gate.Simulation()
    test019.create_simu_test019_phsp_source(sim)

    # make it MT
    sim.number_of_threads = nt = 4

    sl = sim.get_source_user_info("phsp_source_local")
    sl.n /= nt
    sl.entry_start = [sl.n * p for p in range(nt)]
    sl.batch_size = sl.n

    sg = sim.get_source_user_info("phsp_source_global")
    sg.n /= nt
    sg.entry_start = [sl.n * p for p in range(nt)]
    sg.batch_size = sg.n

    print("source entry start", sl.entry_start)
    print("source entry start", sg.entry_start)

    # start simulation
    sim.run()

    # analyse
    is_ok = test019.analyse_test019_phsp_source(sim)

    utility.test_ok(is_ok)

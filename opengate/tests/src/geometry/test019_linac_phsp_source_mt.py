#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import test019_linac_phsp_helpers as test019

if __name__ == "__main__":
    # create sim
    sim = gate.Simulation()
    test019.create_simu_test019_phsp_source(sim, "_phsp_src_mt")

    # make it MT
    sim.number_of_threads = nt = 2

    sl = sim.get_source_user_info("phsp_source_local")
    # In MT, the source now keeps the total requested primaries and scales them
    # internally per worker. Only the PHSP read windows remain thread-specific.
    sl.entry_start = [int(sl.number_of_primaries // nt) * p for p in range(nt)]
    sl.batch_size = int(sl.number_of_primaries // nt)

    sg = sim.get_source_user_info("phsp_source_global")
    sg.entry_start = [int(sg.number_of_primaries // nt) * p for p in range(nt)]
    sg.batch_size = int(sg.number_of_primaries // nt)

    print("source entry start", sl.entry_start)
    print("source entry start", sg.entry_start)

    # start simulation
    sim.run()

    # analyse
    is_ok = test019.analyse_test019_phsp_source(sim)

    utility.test_ok(is_ok)

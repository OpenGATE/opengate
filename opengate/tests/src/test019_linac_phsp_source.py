#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test019_linac_phsp_helpers import *

if __name__ == "__main__":
    # create sim
    sim = gate.Simulation()
    create_simu_test019_phsp_source(sim)

    # start simulation
    sim.run()

    # analyse
    is_ok = analyse_test019_phsp_source(sim.output)

    gate.test_ok(is_ok)

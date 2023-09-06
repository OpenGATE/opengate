#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from test028_ge_nm670_spect_2_helpers import *

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "gate_test028_ge_nm670_spect")

    # create the simulation
    sim = gate.Simulation()

    # main description
    create_spect_simu(sim, paths)

    # mono thread
    ui = sim.user_info
    ui.number_of_threads = 1

    sim.run()

    # check
    is_ok = test_spect_hits(sim.output, paths)

    gate.test_ok(is_ok)

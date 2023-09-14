#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test039_hits_memory_check_helpers import *

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "")

    # create the simulation
    sim = create_simu(8)
    ui = sim.user_info
    ui.random_seed = "auto"

    # go
    sim.run()

    is_ok = test_results(sim.output)

    gate.test_ok(is_ok)

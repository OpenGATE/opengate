#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test039_hits_memory_check_helpers as test39
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "")

    # create the simulation
    sim = test39.create_simu(8)
    ui = sim.user_info
    ui.random_seed = "auto"

    # go
    sim.run()

    is_ok = test39.test_results(sim.output)

    utility.test_ok(is_ok)

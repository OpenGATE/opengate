#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test039_hits_memory_check_helpers as test39
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test039")

    # create the simulation
    sim = test39.create_simu(1, paths)
    sim.random_seed = 987654321

    # go
    sim.run()

    is_ok = test39.test_results(sim, paths)

    utility.test_ok(is_ok)

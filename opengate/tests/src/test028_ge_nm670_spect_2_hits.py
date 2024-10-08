#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test028_ge_nm670_spect_2_helpers as test028
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test028_ge_nm670_spect", output_folder="test028"
    )

    # create the simulation
    sim = gate.Simulation()

    # main description
    test028.create_spect_simu(sim, paths)

    # mono thread
    sim.number_of_threads = 1

    sim.run()

    # check
    is_ok = test028.test_spect_hits(sim, paths)

    utility.test_ok(is_ok)

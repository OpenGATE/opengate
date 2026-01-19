#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test028_ge_nm670_spect_2_helpers as test028
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test028_proj")

    # create the simulation
    sim = gate.Simulation()

    sec = gate.g4_units.second
    cm = gate.g4_units.cm

    # main description
    spect = test028.create_spect_simu(sim, paths, 1)
    test028.test_add_proj(sim)

    # rotate spect
    test028.nm670.rotate_gantry(spect, 10 * cm, -15)

    # go
    sim.run_timing_intervals = [[1 * sec, 2 * sec]]
    sim.run()

    # check
    is_ok = test028.test_spect_root(sim, paths)

    # check
    proj = sim.get_actor("Projection")
    is_ok = test028.test_spect_proj(sim, paths, proj) and is_ok

    utility.test_ok(is_ok)

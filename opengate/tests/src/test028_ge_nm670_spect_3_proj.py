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

    sec = gate.g4_units.second
    cm = gate.g4_units.cm

    # main description
    spect = test028.create_spect_simu(sim, paths, 1, version="_3_proj")
    test028.test_add_proj(sim, fname_suffix="_3_proj")

    # rotate spect
    psd = 6.11 * cm
    p = [0, 0, -(20 * cm + psd)]
    spect.translation, spect.rotation = gate.geometry.utility.get_transform_orbiting(
        p, "y", -15
    )

    sim.run_timing_intervals = [[1 * sec, 2 * sec]]

    # go
    sim.run()

    # check
    is_ok = test028.test_spect_hits(sim, paths, version="3")

    # check
    proj = sim.get_actor("Projection")
    is_ok = test028.test_spect_proj(sim, paths, proj, version="3") and is_ok

    utility.test_ok(is_ok)

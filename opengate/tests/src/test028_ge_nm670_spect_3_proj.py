#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test028_ge_nm670_spect_2_helpers import *

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "gate_test028_ge_nm670_spect")

    # create the simulation
    sim = gate.Simulation()

    # main description
    spect = create_spect_simu(sim, paths, 1)
    test_add_proj(sim, paths)

    # rotate spect
    cm = gate.g4_units("cm")
    psd = 6.11 * cm
    p = [0, 0, -(20 * cm + psd)]
    spect.translation, spect.rotation = gate.get_transform_orbiting(p, "y", -15)

    sec = gate.g4_units("second")
    sim.run_timing_intervals = [[1 * sec, 2 * sec]]

    sim.run()

    # check
    is_ok = test_spect_hits(sim.output, paths, version="3")

    # check
    proj = sim.output.get_actor("Projection")
    is_ok = test_spect_proj(sim.output, paths, proj, version="3") and is_ok

    gate.test_ok(is_ok)

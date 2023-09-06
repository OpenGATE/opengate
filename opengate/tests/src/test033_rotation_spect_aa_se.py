#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test033_rotation_spect_aa_helpers import *

if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()
    sources = create_test(sim)

    # AA mode
    for source in sources:
        source.direction.acceptance_angle.skip_policy = "SkipEvents"

    # go
    sim.run()

    # check
    is_ok = evaluate_test(sim.output, sources, 10, 5908066)

    gate.test_ok(is_ok)

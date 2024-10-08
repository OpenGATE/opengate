#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test033_rotation_spect_aa_helpers as test033
from opengate.tests import utility

if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()
    sources = test033.create_test(sim)

    # AA mode
    for source in sources:
        source.direction.acceptance_angle.skip_policy = "SkipEvents"

    # go
    sim.run()

    # check
    is_ok = test033.evaluate_test(sim, sources, 10, 5908066)

    utility.test_ok(is_ok)

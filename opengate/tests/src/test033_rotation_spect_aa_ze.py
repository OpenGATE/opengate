#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test033_rotation_spect_aa_helpers as test033
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test033")

    # create the simulation
    sim = gate.Simulation()
    sources = test033.create_test(sim)

    # AA mode
    for source in sources:
        source.direction.acceptance_angle.skip_policy = "ZeroEnergy"

    # go
    sim.run()

    # check
    is_ok = test033.evaluate_test(sim, sources, 10, 5905908)

    utility.test_ok(is_ok)

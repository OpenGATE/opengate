#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test038_gan_phsp_spect_gan_helpers as t38
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test038_gan_phsp_spect", "test038"
    )

    # create the simulation
    sim = gate.Simulation()
    condition_generator = t38.create_simulation(sim, paths)

    gsource = sim.get_source_user_info("gaga")
    gsource.skip_policy = "ZeroEnergy"  # this is SkipEvents by default

    # go (cannot be spawn in another process)
    sim.run(start_new_process=False)

    # test
    all_cond = condition_generator.all_cond
    t38.analyze_results(sim, paths, all_cond)

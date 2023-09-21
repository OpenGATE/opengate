#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test038_gan_phsp_spect_gan_helpers import *

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "gate_test038_gan_phsp_spect")
    paths.output_ref = paths.output_ref / "test038"

    # create the simulation
    sim = gate.Simulation()
    condition_generator = create_simulation(sim, paths)

    gsource = sim.get_source_user_info("gaga")
    gsource.skip_policy = "ZeroEnergy"  # this is SkipEvents by default

    # go (cannot be spawn in another process)
    sim.run(start_new_process=False)

    # test
    all_cond = condition_generator.all_cond
    analyze_results(sim.output, paths, all_cond)

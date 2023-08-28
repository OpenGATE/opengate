#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test038_gan_phsp_spect_gan_helpers import *

paths = gate.get_default_test_paths(__file__, "gate_test038_gan_phsp_spect")
paths.output_ref = paths.output_ref / "test038"

# create the simulation
sim = gate.Simulation()
ui = sim.user_info
ui.number_of_threads = 2
condition_generator = create_simulation(sim, paths)

# go (cannot be spawn in another process)
sim.run(start_new_process=False)

# test
all_cond = condition_generator.all_cond
analyze_results(sim.output, paths, all_cond)

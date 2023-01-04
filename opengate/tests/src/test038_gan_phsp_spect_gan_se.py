#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test038_gan_phsp_spect_gan_helpers import *

paths = gate.get_default_test_paths(__file__, "gate_test038_gan_phsp_spect")
paths.output_ref = paths.output_ref / "test038_ref"

# create the simulation
sim = gate.Simulation()
condition_generator = create_simulation(sim, paths)

gsource = sim.get_source_user_info("gaga")
gsource.skip_policy = "SkipEvents"  # this is SkipEvents by default

# go (cannot be spawn in another process)
output = sim.start(False)

# test
all_cond = condition_generator.all_cond
analyze_results(output, paths, all_cond)

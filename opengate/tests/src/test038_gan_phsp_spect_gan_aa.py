#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test038_gan_phsp_spect_gan_helpers import *

paths = gate.get_default_test_paths(__file__, "gate_test038_gan_phsp_spect")
paths.output_ref = paths.output_ref / "test038_ref"

# create the simulation
sim = gate.Simulation()
condition_generator = create_simulation(sim, paths, None)

# add AA
gsource = sim.get_source_user_info("gaga")
gsource.skip_policy = "SkipEvents"
gsource.direction.acceptance_angle.volumes = ["spect1"]
gsource.direction.acceptance_angle.intersection_flag = True
gsource.direction.acceptance_angle.normal_flag = False
gsource.direction.acceptance_angle.skip_policy = "SkipEvents"
# gsource.batch_size = 2e4

# change output names
stat = sim.get_actor_user_info("Stats")
stat.output = paths.output / "test038_gan_aa_stats.txt"
proj = sim.get_actor_user_info("Projection_spect1_crystal")
proj.output = paths.output / "test038_gan_aa_proj.mhd"
singles = sim.get_actor_user_info("Singles_spect1_crystal")
singles.output = paths.output / "test038_gan_aa_singles.root"

# go (cannot be spawn in another process)
output = sim.start(False)

#
print()
stat = output.get_actor("Stats")
print(stat)

s = output.get_source("gaga")
print(f"Source, nb of skipped particles (absorbed) : {s.fTotalSkippedEvents}")
print(f"Source, nb of zeros   particles (absorbed) : {s.fTotalZeroEvents}")

# test
# all_cond = condition_generator.all_cond
# analyze_results(output, paths, all_cond)

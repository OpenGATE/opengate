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
    sim.progress_bar = True
    condition_generator = t38.create_simulation(sim, paths, None)

    # add AA
    gsource = sim.get_source_user_info("gaga")
    gsource.skip_policy = "SkipEvents"
    gsource.direction.angular_acceptance.target_volumes = ["spect1"]
    gsource.direction.angular_acceptance.enable_intersection_check = True
    gsource.direction.angular_acceptance.enable_angle_check = False
    gsource.direction.angular_acceptance.max_rejection = 20000
    gsource.direction.angular_acceptance.policy = "Rejection"
    gsource.direction.angular_acceptance.skip_policy = "SkipEvents"
    # gsource.batch_size = 2e4

    # change output names
    stat = sim.actor_manager.get_actor("Stats")
    stat.output_filename = "test038_gan_aa_stats.txt"
    proj = sim.actor_manager.get_actor("Projection_spect1_crystal")
    proj.output_filename = "test038_gan_aa_proj.mhd"
    singles = sim.actor_manager.get_actor("Singles_spect1_crystal")
    singles.output_filename = "test038_gan_aa_singles.root"

    # go
    sim.run()  # start_new_process=True)

    #
    print()
    s = sim.source_manager.get_source("gaga")
    ref_se = 220534
    t_se = (ref_se - s.total_skipped_events) / ref_se * 100
    tol = 10
    is_ok = t_se < tol
    utility.print_test(
        is_ok,
        f"Source, nb of skipped particles (absorbed) : {s.total_skipped_events} {t_se:0.2f}% (tol = {tol}, {ref_se})",
    )

    print(
        f"Source, nb of zeros particles (absorbed) : {s.total_zero_events} (should be around 5)"
    )

    stats = sim.get_actor("Stats")
    stats_ref = utility.read_stats_file(paths.output_ref / "test038_gan_aa_stats.txt")
    # do not compare steps
    stats_ref.counts.steps = stats.counts.steps
    is_ok = utility.assert_stats(stats, stats_ref, 0.02) and is_ok

    stats.counts.events += s.total_skipped_events
    print("Number of events is increased by the nb of skipped events")
    print(stats)

    # image
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test038_gan_aa_proj.mhd",
            paths.output / "test038_gan_aa_proj_counts.mhd",
            tolerance=70,
            axis="x",
            sum_tolerance=2.75,
            ignore_value_data2=0,
            apply_ignore_mask_to_sum_check=False,  # reproduce legacy behavior
        )
        and is_ok
    )

    utility.test_ok(is_ok)

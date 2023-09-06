#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test038_gan_phsp_spect_gan_helpers import *

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "gate_test038_gan_phsp_spect")
    paths.output_ref = paths.output_ref / "test038"

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
    output = sim.start(True)

    #
    print()
    s = output.get_source("gaga")
    ref_se = 220534
    t_se = (ref_se - s.fTotalSkippedEvents) / ref_se * 100
    tol = 10
    is_ok = t_se < tol
    gate.print_test(
        is_ok,
        f"Source, nb of skipped particles (absorbed) : {s.fTotalSkippedEvents} {t_se:0.2f}% (tol = {tol}, {ref_se})",
    )

    print(
        f"Source, nb of zeros particles (absorbed) : {s.fTotalZeroEvents} (should be around 5)"
    )

    stats = output.get_actor("Stats")
    stats_ref = gate.read_stat_file(paths.output_ref / "test038_gan_aa_stats.txt")
    # do not compare steps
    stats_ref.counts.step_count = stats.counts.step_count
    is_ok = gate.assert_stats(stats, stats_ref, 0.02) and is_ok

    stats.counts.event_count += s.fTotalSkippedEvents
    print("Number of events is increased by the nb of skipped events")
    print(stats)

    # image
    is_ok = (
        gate.assert_images(
            paths.output_ref / "test038_gan_aa_proj.mhd",
            paths.output / "test038_gan_aa_proj.mhd",
            stats,
            tolerance=70,
            axis="x",
            sum_tolerance=2.6,
        )
        and is_ok
    )

    gate.test_ok(is_ok)

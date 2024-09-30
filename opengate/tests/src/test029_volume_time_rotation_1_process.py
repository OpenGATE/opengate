#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test029_volume_time_rotation_helpers as test029
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test029_volume_time_rotation", "test029"
    )

    # create the main simulation object
    sim = gate.Simulation()

    # create sim without AA
    test029.create_simulation(sim, False, paths)

    # for later reference, get the actors that were created by the helper function above
    proj_actor = sim.actor_manager.get_actor("Projection")
    stats = sim.actor_manager.get_actor("Stats")

    # initialize & start
    sim.run(start_new_process=True)

    # -------------------------
    gate.exception.warning("Compare stats")
    print(stats)
    stats_ref = utility.read_stat_file(paths.output_ref / "stats029.txt")
    print(
        f"Number of steps was {stats.counts.steps}, forced to the same value (because of angle acceptance). "
    )
    stats.counts.steps = stats_ref.counts.steps  # force to id
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.02)
    print(is_ok)

    gate.exception.warning("Compare images")
    # read image and force change the offset to be similar to old Gate
    is_ok = (
        utility.assert_images(
            paths.output_ref / "proj029.mhd",
            proj_actor.get_output_path(),  # get the path by asking the actor; better than hard-code the path
            stats,
            tolerance=59,
            ignore_value=0,
            axis="x",
            sum_tolerance=2,
        )
        and is_ok
    )
    print(is_ok)

    utility.test_ok(is_ok)

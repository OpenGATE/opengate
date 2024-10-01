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
    test029.create_simulation(sim, True, paths)

    # for later reference, get the actors that were created by the helper function above
    proj_actor = sim.actor_manager.get_actor("Projection")
    stats = sim.actor_manager.get_actor("Stats")

    # initialize & start
    sim.run()

    """
    WARNING when "angle_acceptance_volume" is enabled, it is a bit faster (+50%) but the result is not
    exactly the same as without. This is because, even if the initial particle is not in the direction of
    the spect system, it can scatter and still reach the detector.

    We don't have the collimator here (to accelerate the simulation), this is why the difference is not negligible.

    The (fake) reference is computed by scaling the ref by 90% (test029_volume_time_rotation_1.py)
    """

    gate.exception.warning("Compare stats")
    print(stats)
    stats_ref = utility.read_stat_file(paths.output_ref / "stats029.txt")
    print(
        f"Number of steps was {stats.counts.steps}, forced to the same value (because of angle acceptance). "
    )
    stats.counts.steps = stats_ref.counts.steps  # force these to be identical
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.01)
    print(is_ok)

    gate.exception.warning("Compare images")
    # read image and force change the offset to be similar to old Gate
    is_ok = (
        utility.assert_images(
            paths.output_ref / "proj029_scaled.mhd",
            proj_actor.get_output_path(),  # get the path by asking the actor; better than hard-code the path
            stats,
            tolerance=60,
            ignore_value=0,
            axis="x",
            sum_tolerance=6,
        )
        and is_ok
    )
    print(is_ok)

    utility.test_ok(is_ok)

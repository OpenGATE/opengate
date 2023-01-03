#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test029_volume_time_rotation_helpers import *

paths = gate.get_default_test_paths(__file__, "gate_test029_volume_time_rotation")

# create the main simulation object
sim = gate.Simulation()

# create sim without AA
create_simulation(sim, True)

# initialize & start
output = sim.start()

"""
WARNING when "angle_acceptance_volume" is enabled, it is a bit faster (+50%) but the result is not
exactly the same as without. This is because, even if the initial particle is not in the direction of
the spect system, it can scatter and still reach the detector.

We don't have the collimator here (to
faster the simulation), this is why the difference is not negligible.

The (fake) reference is computed by scaling the ref by 90% (test029_volume_time_rotation_1.py)
"""

gate.warning("Compare stats")
stats = gate.read_stat_file(paths.output / "stats029.txt")
print(stats)
stats_ref = gate.read_stat_file(paths.output_ref / "stats029.txt")
print(
    f"Number of steps was {stats.counts.step_count}, forced to the same value (because of angle acceptance). "
)
stats.counts.step_count = stats_ref.counts.step_count  # force to id
is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.01)
print(is_ok)

gate.warning("Compare images")
# read image and force change the offset to be similar to old Gate
is_ok = (
    gate.assert_images(
        paths.output_ref / "proj029_scaled.mhd",
        paths.output / "proj029.mhd",
        stats,
        tolerance=50,
        ignore_value=0,
        axis="x",
        sum_tolerance=1,
    )
    and is_ok
)
print(is_ok)

gate.test_ok(is_ok)

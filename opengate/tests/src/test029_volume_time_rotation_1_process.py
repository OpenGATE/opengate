#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test029_volume_time_rotation_helpers import *

paths = gate.get_default_test_paths(__file__, "gate_test029_volume_time_rotation")

# create the main simulation object
sim = gate.Simulation()

# create sim without AA
create_simulation(sim, False)

# initialize & start
output = sim.start(True)

"""
# use to create the (fake) reference for test029_volume_time_rotation_2.py
import itk
scaling = 0.90
img = itk.imread(str(paths.output_ref / "proj029.mhd"))
arr = itk.array_view_from_image(img)
arr *= scaling
itk.imwrite(img, str(paths.output_ref / "proj029_scaled.mhd"))
"""

# -------------------------
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
        paths.output_ref / "proj029.mhd",
        paths.output / "proj029.mhd",
        stats,
        tolerance=47,
        ignore_value=0,
        axis="x",
        sum_tolerance=0.5,
    )
    and is_ok
)
print(is_ok)

gate.test_ok(is_ok)

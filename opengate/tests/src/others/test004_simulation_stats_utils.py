#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.actors.simulation_stats_helpers import *
import opengate.tests.utility as utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test004")

    # Gate mac/main.mac
    print(paths.output_ref)
    stats_ref = utility.read_stats_file(paths.output_ref / "gate9_stats.txt")
    test_ref = utility.read_stats_file(paths.output_ref / "stats.txt")

    print(stats_ref)
    print(test_ref)

    s = sum_stats(stats_ref, test_ref)
    print(s)

    write_stats(s, paths.output / "merged_stats.txt")
    s = utility.read_stats_file(paths.output / "merged_stats.txt")

    # compare merged stats
    ref_merged_stats = utility.read_stats_file(paths.output_ref / "merged_stats.txt")
    is_ok = utility.assert_stats(ref_merged_stats, s, tolerance=1e-6)

    # compare json
    print(ref_merged_stats.counts)
    print(s.counts)
    is_ok = (
        utility.dict_compare(ref_merged_stats.counts, s.counts, tolerance=1e-6)
        and is_ok
    )

    utility.test_ok(is_ok)

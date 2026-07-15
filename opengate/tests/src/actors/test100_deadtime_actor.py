#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test100_deadtime_helpers import (
    check_gate_deadtime,
    DeadTimePolicy,
)
from test100_deadtime_simulation import create_simulation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test100", "test100")

    sim, dt, root_filename = create_simulation(paths, num_threads=1)

    test_all_parameter_combinations = False

    all_tests_ok = True

    for policy in [
        DeadTimePolicy.NonParalyzable,
        DeadTimePolicy.Paralyzable,
    ]:
        dt.policy = policy.name

        sim.run(start_new_process=True)

        all_match = check_gate_deadtime(
            root_filename,
            "Singles_before_deadtime",
            "Singles_after_deadtime",
            dt.dead_time,
            policy,
        )

        if not all_match:
            print(f"Dead time test failed for {policy}")
            all_tests_ok = False

    utility.test_ok(all_tests_ok)

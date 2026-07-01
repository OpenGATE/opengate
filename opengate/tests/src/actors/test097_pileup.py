#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from test097_pileup_helpers import (
    check_gate_pileup,
    TimeWindowPolicy,
    PositionAttributePolicy,
    AttributePolicy,
)
from test097_pileup_simulation import create_simulation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test097", "test097_pileup"
    )

    sim, pu, root_filename = create_simulation(paths, num_threads=1)

    test_all_parameter_combinations = False

    if test_all_parameter_combinations:
        tested_parameter_combinations = []
        for twp in [
            TimeWindowPolicy.NonParalyzable,
            TimeWindowPolicy.Paralyzable,
            TimeWindowPolicy.EnergyWinnerParalyzable,
        ]:
            for pap in [
                PositionAttributePolicy.EnergyWeightedCentroid,
                PositionAttributePolicy.EnergyWinner,
            ]:
                for ap in [
                    AttributePolicy.First,
                    AttributePolicy.EnergyWinner,
                    AttributePolicy.Last,
                ]:
                    tested_parameter_combinations.append((twp, pap, ap))
    else:
        tested_parameter_combinations = [
            # Default
            (
                TimeWindowPolicy.NonParalyzable,
                PositionAttributePolicy.EnergyWeightedCentroid,
                AttributePolicy.First,
            ),
            # GATE 9 behavior
            (
                TimeWindowPolicy.EnergyWinnerParalyzable,
                PositionAttributePolicy.EnergyWinner,
                AttributePolicy.EnergyWinner,
            ),
        ]

    all_tests_ok = True

    for c in tested_parameter_combinations:
        twp, pap, ap = c

        pu.time_window_policy = twp.name
        pu.position_attribute_policy = pap.name
        pu.attribute_policy = ap.name

        sim.run(start_new_process=True)

        all_match = check_gate_pileup(
            root_filename,
            "Singles_before_pileup",
            "Singles_after_pileup",
            pu.time_window,
            twp,
            pap,
            ap,
        )

        if not all_match:
            print(f"Pileup test failed for {twp}, {pap}, {ap}")
            all_tests_ok = False

    utility.test_ok(all_tests_ok)

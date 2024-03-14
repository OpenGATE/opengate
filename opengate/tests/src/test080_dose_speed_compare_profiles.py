#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test080_dose_speed_test_helpers import plot_profile_comparison, test_scenarios

if __name__ == "__main__":
    scenarios = dict(
        (k, s) for k, s in test_scenarios.items() if s["number_of_threads"] == 4
    )
    plot_profile_comparison(scenarios, n_primaries=1e4)

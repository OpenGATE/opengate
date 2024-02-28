#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility

import matplotlib.pyplot as plt
import numpy as np
import json

from test080_dose_speed_test_helpers import run_simu, create_dict_key, test_paths


if __name__ == "__main__":

    scenarios = {}
    s = {
        "storage_method": "atomic",
        "number_of_threads": 4,
        "name": "std::deque<std::atomic<double>>",
    }
    scenarios[create_dict_key(s)] = s
    s = {
        "storage_method": "atomic_vec_pointer",
        "number_of_threads": 4,
        "name": "std::vector<std::atomic<double>>*",
    }
    scenarios[create_dict_key(s)] = s

    n_primaries = 1e4
    pixel_size_list = ["small", "large", "single"]

    for k, s in scenarios.items():
        reattempts = []
        total_writes = []
        for ps in pixel_size_list:
            print(30 * "*")
            print(f"Running {k} with {n_primaries} primaries and pixel size '{ps}'.")
            print(30 * "*")
            output = run_simu(
                n_primaries,
                s["storage_method"],
                s["number_of_threads"],
                pixel_size=ps,
                count_write_attempts=True,
            )
            reattempts.append(output.hook_log[0])
            total_writes.append(output.hook_log[1])

        s["reattempts"] = reattempts
        s["total_writes"] = total_writes
        s["n_primaries"] = n_primaries
        s["pixel_size_list"] = pixel_size_list

    with open(
        test_paths.output / "results_doseactor_speed_comparison_reattempts.json", "w"
    ) as fp:
        json.dump(scenarios, fp, indent=4)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import opengate as gate
from opengate.tests import utility
import numpy as np


def main():
    paths = utility.get_default_test_paths(__file__, None, output_folder="test111")

    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.number_of_threads = 1  # FIXME to check in MT

    box = sim.add_volume("Box", "box")
    box.size = [10.0, 10.0, 10.0]

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.n = [5e6, 5e6]
    source.direction.type = "iso"
    source.energy.mono = 1.0 * gate.g4_units.MeV

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sim.run_timing_intervals = [[0.0, 1.0], [1.0, 2.0]]

    # Progress status report
    status_file = paths.output / "progress_status.json"
    sim.progress_status_filename = status_file
    sim.progress_status_interval = 1 * gate.g4_units.s

    print(f"Status file will be written in {status_file}")
    print(f"watch -n 0.1 jq . {status_file})")

    # go
    sim.run()
    print(stats)

    is_ok = status_file.exists()
    if is_ok:
        with open(status_file, "r") as f:
            data = json.load(f)

        print("\nProgress status JSON content:")
        print(json.dumps(data, indent=2))
        N = np.sum(np.array(source.n))
        print("Total events expected = ", N)

        is_ok = is_ok and data.get("status") == "completed"
        is_ok = is_ok and "elapsed_time_seconds" in data
        is_ok = is_ok and data.get("number_of_runs") == 2
        is_ok = is_ok and data.get("progress_percentage") == 100.0
        is_ok = is_ok and data.get("total_events") == N

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()

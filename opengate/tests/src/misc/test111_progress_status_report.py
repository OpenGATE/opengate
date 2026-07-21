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
    sim.number_of_threads = 2

    box = sim.add_volume("Box", "box")
    box.size = [10.0, 10.0, 10.0]

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.n = [2e6 / sim.number_of_threads, 2e6 / sim.number_of_threads]
    source.direction.type = "iso"
    source.energy.mono = 1.0 * gate.g4_units.MeV

    source = sim.add_source("GenericSource", "source2")
    source.particle = "gamma"
    source.activity = 2e6 * gate.g4_units.Bq / sim.number_of_threads
    source.direction.type = "iso"
    source.energy.mono = 1.0 * gate.g4_units.MeV

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sec = gate.g4_units.s
    sim.run_timing_intervals = [[0.0, 1.0 * sec], [1.0 * sec, 2.0 * sec]]

    # Progress status report
    status_file = paths.output / "progress_status.json"
    sim.progress_status_filename = status_file
    sim.progress_status_interval = 0.5 * gate.g4_units.s

    print(f"Status file will be written in {status_file}")
    # go
    sim.run()
    print(stats)

    is_ok = status_file.exists()
    if is_ok:
        with open(status_file, "r") as f:
            data = json.load(f)

        print("\nProgress status JSON content:")
        print(json.dumps(data, indent=2))

        # Expected expected total events = 4e6 from source1 (2e6/2*2 runs*2 threads) + 4e6 from source2 activity
        is_ok = is_ok and data.get("status") == "completed"
        is_ok = is_ok and "elapsed_time_seconds" in data
        is_ok = is_ok and data.get("run_total") == 2
        is_ok = is_ok and data.get("events_progress") == 100.0
        is_ok = is_ok and data.get("simulation_time_progress") == 100.0
        is_ok = is_ok and data.get("simulation_time_total") == 2.0
        is_ok = is_ok and data.get("events_expected") == 8000000
        is_ok = is_ok and data.get("events_total") > 0

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()

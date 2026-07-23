#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import opengate as gate
from opengate.tests import utility
import numpy as np
import os


def main():
    paths = utility.get_default_test_paths(__file__, None, output_folder="test111")

    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.number_of_threads = 2

    # for windows, use only 1 thread
    if os.name == "nt":
        sim.number_of_threads = 1

    box = sim.add_volume("Box", "box")
    box.size = [10.0, 10.0, 10.0]

    source1 = sim.add_source("GenericSource", "source")
    source1.particle = "gamma"
    source1.n = [1e6 / sim.number_of_threads, 1e6 / sim.number_of_threads]
    source1.direction.type = "iso"
    source1.energy.mono = 1.0 * gate.g4_units.MeV

    source2 = sim.add_source("GenericSource", "source2")
    source2.particle = "gamma"
    source2.activity = 1e6 * gate.g4_units.Bq / sim.number_of_threads
    source2.direction.type = "iso"
    source2.energy.mono = 1.0 * gate.g4_units.MeV

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sec = gate.g4_units.s
    sim.run_timing_intervals = [[0.0, 1.0 * sec], [1.0 * sec, 2.0 * sec]]

    # Progress status report
    status_file = paths.output / "progress_status.json"
    status_reporter = gate.progress_status(status_file)

    # Custom progress hook verification
    custom_hook_calls = []

    def custom_hook(sim_engine, status="running"):
        # delegate to progress_status
        data = status_reporter(sim_engine, status)
        custom_hook_calls.append(data)
        print(
            f"[Custom Progress Hook] run = {data['run_index']} / {data['run_total']}, "
            f"events = {data['events_total']}, sim time = {data['simulation_time_current']} / {data['simulation_time_total']}"
        )

    sim.progress_hook = custom_hook
    sim.progress_hook_interval = 0.5 * gate.g4_units.s
    # conventional simulation should use :
    # sim.progress_hook = gate.progress_status(status_file)

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

        expected_N = data.get("events_expected")
        print("Total events expected = ", expected_N)

        is_ok = is_ok and data.get("status") == "completed"
        is_ok = is_ok and "elapsed_time_seconds" in data
        is_ok = is_ok and "estimated_time_remaining_seconds" in data
        is_ok = is_ok and data.get("estimated_time_remaining_seconds") == 0.0
        is_ok = is_ok and data.get("run_total") == 2
        is_ok = is_ok and data.get("events_progress") == 100.0
        is_ok = is_ok and data.get("simulation_time_progress") == 100.0
        is_ok = is_ok and data.get("simulation_time_total") == 2.0
        is_ok = is_ok and data.get("events_expected") == expected_N
        is_ok = is_ok and data.get("events_total") > 0

        # Check data saved in custom_hook_calls
        is_ok = is_ok and len(custom_hook_calls) > 0
        is_ok = is_ok and custom_hook_calls[-1].get("status") == "completed"

        # Check event numbers in captured calls
        prev_events = -1
        intermediate_calls = [
            c for c in custom_hook_calls if c.get("status") != "completed"
        ]

        for step_idx, call_data in enumerate(intermediate_calls, start=1):
            step_ok = True
            step_ok = step_ok and call_data.get("events_expected") == expected_N
            current_ev = call_data.get("events_total", 0)
            elapsed = call_data.get("elapsed_time_seconds", 0.0)
            events_prog = call_data.get("events_progress", 0.0)

            step_ok = step_ok and (current_ev >= prev_events)
            step_ok = step_ok and (0 <= current_ev < expected_N)

            expected_prog = round((current_ev / float(expected_N)) * 100.0, 2)
            step_ok = step_ok and (abs(events_prog - expected_prog) < 0.1)
            prev_events = current_ev

            utility.print_test(
                step_ok,
                f"step {step_idx} elapsed={elapsed}s events_total={current_ev} ({events_prog}%)",
            )
            is_ok = is_ok and step_ok

        # Verify the final completed call generated all expected events
        is_ok = (
            is_ok
            and abs(custom_hook_calls[-1].get("events_total") - expected_N) < 10000
        )

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Validate profiler propagation through a local split-run-merge campaign."""

import json
import shutil

import opengate as gate
from opengate.tests import utility


def build_simulation(output_dir):
    """Create a minimal mergeable simulation for profiling orchestration."""
    sim = gate.Simulation()
    sim.output_dir = output_dir
    sim.random_seed = 123456
    sim.g4_verbose = False
    sim.visu = False

    source = sim.add_source("GenericSource", "source")
    source.particle = "geantino"
    source.number_of_primaries = 20

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "stats.json"
    stats.keep_data_per_run = True
    return sim


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test115_jobs")
    shutil.rmtree(paths.output, ignore_errors=True)
    paths.output.mkdir(parents=True)

    # A monolithic subprocess returns its process-local engine timings to the
    # profiler attached to the live parent simulation.
    monolithic_simulation = build_simulation(paths.output / "monolithic")
    monolithic_simulation.profiler.enable()
    monolithic_simulation.run(start_new_process=True)
    monolithic_paths = {
        record["path"]
        for record in monolithic_simulation.profiler.to_dictionary()["records"]
    }
    is_ok = utility.print_test(
        "engine.transport" in monolithic_paths,
        "Monolithic subprocess transport timing is recovered by the parent",
    )

    simulation = build_simulation(paths.output / "merged")
    simulation.profiler.enable()
    controller = simulation.run(
        number_of_jobs=2,
        wait_for_result=True,
        merge_after_run=True,
        campaign_dir=paths.output / "campaign",
        poll_interval=0.1,
        timeout=60,
    )

    aggregate_path = (
        controller.campaign_dir / "profiling" / "campaign_profile.json"
    )
    with aggregate_path.open(encoding="utf-8") as stream:
        aggregate = json.load(stream)
    record_paths = {record["path"] for record in aggregate["records"]}

    is_ok = (
        utility.print_test(
            aggregate_path.exists(),
            "Split-run-merge writes an aggregate campaign profile",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            any("split_manager.total" in path for path in record_paths),
            "Aggregate profile contains split-manager timing",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            any(path.endswith("simulation.engine.transport") for path in record_paths),
            "Aggregate profile contains child transport timing",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            any("merge_manager.execute_merge" in path for path in record_paths),
            "Aggregate profile contains merge execution timing",
        )
        and is_ok
    )

    utility.test_ok(is_ok)

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

    # A monolithic subprocess returns its process-local engine timings to its
    # execution controller.
    monolithic_simulation = build_simulation(paths.output / "monolithic")
    monolithic_controller = monolithic_simulation.run(
        start_new_process=True, profiling=True
    )
    monolithic_paths = {
        record["path"]
        for record in monolithic_controller.profiler.to_dictionary()["records"]
    }
    is_ok = utility.print_test(
        "simulation.engine.transport" in monolithic_paths,
        "Monolithic subprocess transport timing is recovered by the parent",
    )
    is_ok = (
        utility.print_test(
            isinstance(monolithic_controller, gate.MonolithicRunController)
            and monolithic_controller.profiler.enabled
            and not hasattr(monolithic_simulation, "profiler"),
            "Monolithic profiling belongs to the returned execution controller",
        )
        and is_ok
    )

    simulation = build_simulation(paths.output / "merged")
    controller = simulation.run(
        number_of_jobs=2,
        wait_for_result=True,
        merge_after_run=True,
        campaign_dir=paths.output / "campaign",
        poll_interval=0.1,
        timeout=60,
        profiling=True,
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
            not hasattr(simulation, "profiler") and controller.profiler.enabled,
            "Multi-job profiling belongs to the returned execution controller",
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

    # An explicit false override applies to the campaign and all materialized
    # child jobs, including campaigns that were originally profiled.
    gate.jobs_run(
        controller.campaign_dir,
        backend="local_sequential",
        detach=False,
        profiling=False,
    )
    with controller.manifest_path.open(encoding="utf-8") as stream:
        disabled_manifest = json.load(stream)
    profiling_disabled_everywhere = not disabled_manifest["profiling"]["enabled"]
    for job in disabled_manifest["jobs"]:
        metadata_path = (
            controller.campaign_dir
            / job["folder_name"]
            / job["metadata_filename"]
        )
        with metadata_path.open(encoding="utf-8") as stream:
            metadata = json.load(stream)
        profiling_disabled_everywhere &= not metadata["profiling"]["enabled"]
    is_ok = (
        utility.print_test(
            profiling_disabled_everywhere,
            "Explicit profiling=False disables the campaign and all child jobs",
        )
        and is_ok
    )

    utility.test_ok(is_ok)

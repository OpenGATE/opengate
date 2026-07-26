#!/usr/bin/env python3

import shutil
import time
import opengate as gate
from pathlib import Path
from opengate.tests import utility
from opengate.serialization import load_json_with_retry


def build_simulation(output_path, run_timing_intervals, source_n):
    """Build a split-ready simulation with a simple mergeable actor output.

    We add a Statistics actor with per-run output enabled because it gives us a
    lightweight container-backed actor output whose planned merge contributions
    are easy to inspect without executing the simulation.
    """

    sim = gate.Simulation()
    sim.output_dir = output_path

    world = sim.world
    world.size = [1.0 * gate.g4_units.m] * 3

    box = sim.add_volume("Box", "waterbox")
    box.size = [10.0 * gate.g4_units.cm] * 3
    box.material = "G4_WATER"

    source = sim.add_source("GenericSource", "point_source")
    source.particle = "gamma"
    source.n = source_n
    source.position.type = "point"
    source.position.translation = [0.0, 0.0, 0.0]
    source.direction.type = "iso"
    source.energy.mono = 1.0 * gate.g4_units.MeV

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.json"
    stats.keep_data_per_run = True

    sim.run_timing_intervals = run_timing_intervals
    return sim


def wait_until_jobs_completed(split_root, timeout=60):
    manifest_path = split_root / "jobs_manifest.json"
    manifest = load_json_with_retry(manifest_path)
    deadline = time.time() + timeout
    last_statuses = []
    while time.time() < deadline:
        last_statuses = []
        for job in manifest["jobs"]:
            status_path = split_root / job["folder_name"] / "job_execution_status.json"
            if not status_path.exists():
                continue
            status = load_json_with_retry(status_path)
            last_statuses.append(status.get("status"))
        if len(last_statuses) == len(manifest["jobs"]) and all(
            status == "completed" for status in last_statuses
        ):
            return last_statuses
        time.sleep(0.5)
    raise RuntimeError(
        f"Timed out waiting for split jobs to complete. Last observed statuses: {last_statuses}"
    )


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test113")
    sec = gate.g4_units.s
    is_ok = True

    split_root = paths.output / "merge_context_split"
    shutil.rmtree(split_root, ignore_errors=True)
    shutil.rmtree(paths.output / "merge_context_input", ignore_errors=True)
    shutil.rmtree(paths.output / "reference", ignore_errors=True)
    shutil.rmtree(paths.output / "merged", ignore_errors=True)

    sim = build_simulation(
        paths.output / "merge_context_input",
        [(0.0 * sec, 1.0 * sec), (2.0 * sec, 5.0 * sec)],
        [10, 30],
    )
    split_root = gate.jobs_split(
        sim,
        3,
        split_root,
        policy="split_in_time_total",
    )

    merge_manager = gate.jobs_merge(split_root, execute=False)
    merge_context = merge_manager.plan_merge()

    print()
    print("MergeContext pretty dump:")
    print("-------------------------")
    merge_context.print_pretty()

    merge_context_dict = merge_context.to_dict()
    informative_sources = merge_context_dict["informative"]["sources"]
    output_inventory = merge_context_dict["instructive"]["output_inventory"]

    utility.print_test(
        sorted(informative_sources.keys()) == [1, 2, 3],
        f"Informative merge-context sources are keyed by job_index: {sorted(informative_sources.keys())}",
    )
    is_ok = sorted(informative_sources.keys()) == [1, 2, 3] and is_ok

    inventory_job_indices = sorted(
        {output_plan["job_index"] for output_plan in output_inventory}
    )
    utility.print_test(
        inventory_job_indices == [1, 2, 3],
        f"Flat output inventory covers job_index values: {inventory_job_indices}",
    )
    is_ok = inventory_job_indices == [1, 2, 3] and is_ok

    utility.print_test(
        informative_sources[1]["local_to_original_run_map"] == [0, 1],
        f"job0001 local-to-original run map: {informative_sources[1]['local_to_original_run_map']}",
    )
    is_ok = informative_sources[1]["local_to_original_run_map"] == [0, 1] and is_ok

    utility.print_test(
        informative_sources[2]["local_to_original_run_map"] == [1],
        f"job0002 local-to-original run map: {informative_sources[2]['local_to_original_run_map']}",
    )
    is_ok = informative_sources[2]["local_to_original_run_map"] == [1] and is_ok

    utility.print_test(
        informative_sources[3]["local_to_original_run_map"] == [1],
        f"job0003 local-to-original run map: {informative_sources[3]['local_to_original_run_map']}",
    )
    is_ok = informative_sources[3]["local_to_original_run_map"] == [1] and is_ok

    stats_plan_job0 = next(
        output_plan
        for output_plan in output_inventory
        if output_plan["job_index"] == 1
        and output_plan["actor_name"] == "Stats"
        and output_plan["output_name"] == "stats"
    )
    stats_contributions_job0 = stats_plan_job0["contributions"]

    utility.print_test(
        len(stats_contributions_job0) == 3,
        f"job0001 planned statistics contributions: {len(stats_contributions_job0)}",
    )
    is_ok = len(stats_contributions_job0) == 3 and is_ok

    utility.print_test(
        [contribution["source_scope"] for contribution in stats_contributions_job0]
        == [0, 1, "merged"],
        f"job0001 source scopes: {[contribution['source_scope'] for contribution in stats_contributions_job0]}",
    )
    is_ok = (
        [contribution["source_scope"] for contribution in stats_contributions_job0]
        == [0, 1, "merged"]
        and is_ok
    )

    utility.print_test(
        [contribution["target_scope"] for contribution in stats_contributions_job0]
        == [0, 1, "merged"],
        f"job0001 target scopes mapped to original runs: {[contribution['target_scope'] for contribution in stats_contributions_job0]}",
    )
    is_ok = (
        [contribution["target_scope"] for contribution in stats_contributions_job0]
        == [0, 1, "merged"]
        and is_ok
    )

    utility.print_test(
        [Path(contribution["output_path"]).name for contribution in stats_contributions_job0]
        == ["stats-run0.json", "stats-run1.json", "stats.json"],
        f"job0001 resolved planned statistics output paths: {[Path(contribution['output_path']).name for contribution in stats_contributions_job0]}",
    )
    is_ok = (
        [Path(contribution["output_path"]).name for contribution in stats_contributions_job0]
        == ["stats-run0.json", "stats-run1.json", "stats.json"]
        and is_ok
    )

    utility.print_test(
        all(contribution["expected_on_disk"] for contribution in stats_contributions_job0),
        "All planned statistics contributions are expected on disk",
    )
    is_ok = (
        all(contribution["expected_on_disk"] for contribution in stats_contributions_job0)
        and is_ok
    )

    utility.print_test(
        all(contribution["mergeable"] for contribution in stats_contributions_job0),
        "All planned statistics contributions are marked mergeable",
    )
    is_ok = (
        all(contribution["mergeable"] for contribution in stats_contributions_job0)
        and is_ok
    )

    utility.print_test(
        stats_plan_job0["merge_coordinator"] == "standard",
        f"job0001 statistics output is assigned to merge coordinator: {stats_plan_job0['merge_coordinator']}",
    )
    is_ok = stats_plan_job0["merge_coordinator"] == "standard" and is_ok

    utility.print_test(
        all(contribution["job_index"] == 1 for contribution in stats_contributions_job0),
        "job0001 planned statistics contributions carry job_index provenance",
    )
    is_ok = (
        all(contribution["job_index"] == 1 for contribution in stats_contributions_job0)
        and is_ok
    )

    utility.print_test(
        all("job_id" in contribution for contribution in stats_contributions_job0),
        "job0001 planned statistics contributions carry job_id provenance",
    )
    is_ok = (
        all("job_id" in contribution for contribution in stats_contributions_job0)
        and is_ok
    )

    print()
    print("Running reference simulation ...")
    reference_sim = build_simulation(
        paths.output / "reference",
        [(0.0 * sec, 1.0 * sec), (2.0 * sec, 5.0 * sec)],
        [10, 30],
    )
    reference_sim.run()

    print("Running split jobs sequentially ...")
    run_summary = gate.jobs_run(split_root, backend="local_sequential")
    print(run_summary)
    wait_until_jobs_completed(split_root)

    print("Merging split jobs ...")
    merge_manager = gate.jobs_merge(split_root, to_path=paths.output / "merged")
    merged_sim = merge_manager.master_simulation

    utility.print_test(
        merged_sim.output_dir == paths.output / "merged",
        f"Merged simulation output dir: {merged_sim.output_dir}",
    )
    is_ok = (merged_sim.output_dir == paths.output / "merged") and is_ok

    is_ok = (
        utility.assert_stats(
            merged_sim.get_actor("Stats"),
            reference_sim.get_actor("Stats"),
            tolerance=[0, 0.10, 0.10],
        )
        and is_ok
    )

    utility.test_ok(is_ok)

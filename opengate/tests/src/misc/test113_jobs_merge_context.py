#!/usr/bin/env python3

import json
import shutil
import time
from pathlib import Path

import itk
import numpy as np
import opengate as gate
import uproot
from opengate.exception import GateMergeError
from opengate.tests import utility
from opengate.serialization import load_json_with_retry


def get_single_voxel_value_from_image(image):
    return float(np.asarray(itk.GetArrayViewFromImage(image)).ravel()[0])


def read_single_voxel_value(path):
    return get_single_voxel_value_from_image(itk.imread(str(path)))


def build_simulation(output_path, run_timing_intervals, source_n):
    """Build a split-ready simulation with standard and ROOT actor outputs.

    The setup is intentionally simple and probes three merge paths at once:
    - ``SimulationStatisticsActor`` for lightweight dictionary-like output
    - ``DoseActor`` for standard image-based actor-output merge
    - ``PhaseSpaceActor`` for ROOT-backed merge via ``RootMergeCoordinator``
    """

    sim = gate.Simulation()
    sim.output_dir = output_path
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 123456789

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    sec = gate.g4_units.s
    nm = gate.g4_units.nm

    world = sim.world
    world.size = [1.0 * m] * 3

    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [20.0 * cm] * 3
    waterbox.material = "G4_WATER"

    source = sim.add_source("GenericSource", "point_source")
    source.particle = "proton"
    # Keep the source energy low and the production cuts very large so the
    # phase-space actor records a stream dominated by one scored step per
    # primary. This makes the EventID remap check meaningful in this test.
    source.energy.mono = 10 * keV
    source.n = source_n
    source.position.type = "disc"
    source.position.radius = 1.0 * nm
    source.position.translation = [0, 0, -9.0 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    sim.physics_manager.global_production_cuts.all = 1.0 * m

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.json"
    stats.keep_data_per_run = True

    # Use one voxel covering the full target so merged image checks reduce to
    # scalar comparisons while still exercising the standard image merge path.
    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = "waterbox"
    dose.size = [1, 1, 1]
    dose.spacing = [20.0 * cm, 20.0 * cm, 20.0 * cm]
    dose.translation = [0, 0, 0]
    dose.dose.active = True
    dose.dose.keep_data_per_run = True
    dose.dose.output_filename = "dose.mhd"

    # Store the first step seen in the water box. This keeps the ROOT output
    # compact while still exercising the ROOT merge path, including per-run
    # identity through auto-injected RunID.
    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = "waterbox"
    phsp.steps_to_store = "first"
    phsp.output_filename = "test113_phsp.root"
    phsp.attributes = ["GlobalTime", "KineticEnergy", "EventID"]
    phsp.keep_data_per_run = True

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


def check_phase_space_root(
    reference_root, merged_root, expected_run_ids, run_timing_intervals
):
    with uproot.open(reference_root) as reference_file:
        reference_tree = reference_file["PhaseSpace"]
        reference_branches = sorted(reference_tree.keys())
        reference_entries = reference_tree.num_entries
        reference_global_time = reference_tree["GlobalTime"].array(library="np")
        reference_kinetic_energy = reference_tree["KineticEnergy"].array(
            library="np"
        )

    with uproot.open(merged_root) as merged_file:
        merged_tree = merged_file["PhaseSpace"]
        merged_branches = sorted(merged_tree.keys())
        merged_entries = merged_tree.num_entries
        merged_global_time = merged_tree["GlobalTime"].array(library="np")
        merged_kinetic_energy = merged_tree["KineticEnergy"].array(library="np")
        merged_run_ids = merged_tree["RunID"].array(library="np")
        merged_event_ids = merged_tree["EventID"].array(library="np")

    is_ok = True
    is_ok = (
        utility.print_test(
            merged_branches == reference_branches,
            f"Merged phase-space branches: {merged_branches}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            merged_entries == reference_entries,
            f"Merged phase-space entries vs reference: {merged_entries} {reference_entries}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.array_equal(np.unique(merged_run_ids), np.asarray(expected_run_ids)),
            f"Merged RunID values: {np.unique(merged_run_ids).tolist()}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            len(np.unique(merged_event_ids)) == len(merged_event_ids),
            f"Merged EventID values are unique: {len(np.unique(merged_event_ids))}/{len(merged_event_ids)}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.all(np.diff(merged_event_ids) >= 0),
            "Merged EventID values are non-decreasing in file order",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.all(np.diff(merged_global_time) >= 0),
            "Merged GlobalTime values are non-decreasing in file order",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            np.isclose(
                np.mean(merged_kinetic_energy),
                np.mean(reference_kinetic_energy),
                rtol=0.05,
                atol=0.0,
            ),
            f"Merged KineticEnergy mean vs reference: {np.mean(merged_kinetic_energy)/gate.g4_units.MeV:.6f} MeV {np.mean(reference_kinetic_energy)/gate.g4_units.MeV:.6f} MeV",
        )
        and is_ok
    )

    for run_id in expected_run_ids:
        run_mask = merged_run_ids == run_id
        run_times = merged_global_time[run_mask]
        run_interval = run_timing_intervals[run_id]
        run_start = run_interval[0] / gate.g4_units.s
        run_stop = run_interval[1] / gate.g4_units.s
        if len(run_times) == 0:
            is_ok = (
                utility.print_test(
                    False,
                    f"Merged ROOT output contains entries for RunID {run_id}",
                )
                and is_ok
            )
            continue
        # In a time-split campaign, concatenation should preserve chronological
        # order, so each RunID block should remain inside its configured
        # original run interval.
        is_ok = (
            utility.print_test(
                run_interval[0] <= np.min(run_times) <= run_interval[1]
                and run_interval[0] <= np.max(run_times) <= run_interval[1],
                f"RunID {run_id} GlobalTime range stays within [{run_start:.6f}, {run_stop:.6f}] s",
            )
            and is_ok
        )
    return is_ok


def run_failure_probe(split_root, broken_output_path):
    broken_output_path = Path(broken_output_path)
    moved_output_path = broken_output_path.with_name(
        f"broken_{broken_output_path.name}"
    )
    shutil.move(broken_output_path, moved_output_path)

    if broken_output_path.suffix == ".mhd":
        raw_path = broken_output_path.with_suffix(".raw")
        moved_raw_path = moved_output_path.with_suffix(".raw")
        if raw_path.exists():
            shutil.move(raw_path, moved_raw_path)

    try:
        gate.jobs_merge(split_root, to_path=split_root.parent / "broken_merge_output")
    except GateMergeError as error:
        return utility.print_test(
            "dose" in str(error) or "Failed to execute standard merge" in str(error),
            f"Intentional broken-dose merge raises GateMergeError: {error}",
        )
    return utility.print_test(
        False,
        "Intentional broken-dose merge should have raised GateMergeError",
    )


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test113")
    sec = gate.g4_units.s
    is_ok = True

    split_root = paths.output / "merge_context_split"
    broken_split_root = paths.output / "merge_context_split_broken"
    shutil.rmtree(split_root, ignore_errors=True)
    shutil.rmtree(broken_split_root, ignore_errors=True)
    shutil.rmtree(paths.output / "merge_context_input", ignore_errors=True)
    shutil.rmtree(paths.output / "merge_context_input_broken", ignore_errors=True)
    shutil.rmtree(paths.output / "reference", ignore_errors=True)
    shutil.rmtree(paths.output / "merged", ignore_errors=True)
    shutil.rmtree(paths.output / "broken_merge_output", ignore_errors=True)

    run_timing_intervals = [(0.0 * sec, 1.0 * sec), (2.0 * sec, 5.0 * sec)]
    source_n = [100, 300]

    sim = build_simulation(
        paths.output / "merge_context_input",
        run_timing_intervals,
        source_n,
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
        len(output_inventory) == 18,
        f"Flat output inventory contains one entry per job and actor output: {len(output_inventory)}",
    )
    is_ok = len(output_inventory) == 18 and is_ok

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

    stats_plan_job1 = next(
        output_plan
        for output_plan in output_inventory
        if output_plan["job_index"] == 1
        and output_plan["actor_name"] == "Stats"
        and output_plan["output_name"] == "stats"
    )
    dose_plan_job1 = next(
        output_plan
        for output_plan in output_inventory
        if output_plan["job_index"] == 1
        and output_plan["actor_name"] == "dose"
        and output_plan["output_name"] == "dose_with_uncertainty"
    )
    phsp_plan_job1 = next(
        output_plan
        for output_plan in output_inventory
        if output_plan["job_index"] == 1
        and output_plan["actor_name"] == "PhaseSpace"
        and output_plan["output_name"] == "root_output"
    )

    utility.print_test(
        stats_plan_job1["merge_coordinator"] == "standard",
        f"Statistics output merge coordinator: {stats_plan_job1['merge_coordinator']}",
    )
    is_ok = stats_plan_job1["merge_coordinator"] == "standard" and is_ok

    utility.print_test(
        dose_plan_job1["merge_coordinator"] == "standard",
        f"Dose output merge coordinator: {dose_plan_job1['merge_coordinator']}",
    )
    is_ok = dose_plan_job1["merge_coordinator"] == "standard" and is_ok

    utility.print_test(
        phsp_plan_job1["merge_coordinator"] == "root",
        f"Phase-space output merge coordinator: {phsp_plan_job1['merge_coordinator']}",
    )
    is_ok = phsp_plan_job1["merge_coordinator"] == "root" and is_ok

    utility.print_test(
        [contribution["source_scope"] for contribution in stats_plan_job1["contributions"]]
        == [0, 1, "merged"],
        f"job0001 statistics source scopes: {[contribution['source_scope'] for contribution in stats_plan_job1['contributions']]}",
    )
    is_ok = (
        [contribution["source_scope"] for contribution in stats_plan_job1["contributions"]]
        == [0, 1, "merged"]
        and is_ok
    )

    utility.print_test(
        [
            Path(contribution["output_path"]).name
            for contribution in dose_plan_job1["contributions"]
            if contribution["item_identifier"] == 0
        ]
        == ["dose-run0.mhd", "dose-run1.mhd", "dose.mhd"],
        f"job0001 resolved planned dose output paths: {[Path(contribution['output_path']).name for contribution in dose_plan_job1['contributions'] if contribution['item_identifier'] == 0]}",
    )
    is_ok = (
        [
            Path(contribution["output_path"]).name
            for contribution in dose_plan_job1["contributions"]
            if contribution["item_identifier"] == 0
        ]
        == ["dose-run0.mhd", "dose-run1.mhd", "dose.mhd"]
        and is_ok
    )

    utility.print_test(
        len(phsp_plan_job1["contributions"]) == 2,
        f"job0001 planned phase-space contributions: {len(phsp_plan_job1['contributions'])}",
    )
    is_ok = len(phsp_plan_job1["contributions"]) == 2 and is_ok

    print()
    print("Running reference simulation ...")
    reference_sim = build_simulation(
        paths.output / "reference",
        run_timing_intervals,
        source_n,
    )
    reference_sim.run()

    print("Running split jobs sequentially ...")
    run_summary = gate.jobs_run(split_root, backend="local_sequential")
    print(run_summary)
    wait_until_jobs_completed(split_root)

    print("Merging split jobs ...")
    merge_manager = gate.jobs_merge(split_root, to_path=paths.output / "merged", execute=True)
    merged_sim = merge_manager.master_simulation

    utility.print_test(
        merged_sim.output_dir == paths.output / "merged",
        f"Merged simulation output dir: {merged_sim.output_dir}",
    )
    is_ok = (merged_sim.output_dir == paths.output / "merged") and is_ok

    utility.print_test(
        merge_manager.merge_planned and merge_manager.merge_executed and merge_manager.merge_finalized,
        f"Merge lifecycle flags: planned={merge_manager.merge_planned} executed={merge_manager.merge_executed} finalized={merge_manager.merge_finalized}",
    )
    is_ok = (
        merge_manager.merge_planned
        and merge_manager.merge_executed
        and merge_manager.merge_finalized
        and is_ok
    )

    is_ok = (
        utility.assert_stats(
            merged_sim.get_actor("Stats"),
            reference_sim.get_actor("Stats"),
            tolerance=[0, 0.10, 0.10],
        )
        and is_ok
    )

    merged_dose = merged_sim.get_actor("dose")
    reference_dose = reference_sim.get_actor("dose")

    for run_index in range(len(run_timing_intervals)):
        merged_run_path = merged_dose.dose.get_output_path(which=run_index)
        reference_run_path = reference_dose.dose.get_output_path(which=run_index)
        merged_run_value = read_single_voxel_value(merged_run_path)
        reference_run_value = read_single_voxel_value(reference_run_path)
        is_ok = (
            utility.print_test(
                np.isclose(
                    merged_run_value,
                    reference_run_value,
                    # Dose images are merged from independent child outputs, so
                    # tiny floating-point differences from accumulation order
                    # are expected even when the physical result is the same.
                    rtol=1e-3,
                    atol=0.0,
                ),
                f"Run {run_index} merged dose vs reference: {merged_run_value:.6e} {reference_run_value:.6e}",
            )
            and is_ok
        )

    merged_dose_path = merged_dose.dose.get_output_path(which="merged")
    reference_dose_path = reference_dose.dose.get_output_path(which="merged")
    merged_dose_value = read_single_voxel_value(merged_dose_path)
    reference_dose_value = read_single_voxel_value(reference_dose_path)
    is_ok = (
        utility.print_test(
            np.isclose(
                merged_dose_value,
                reference_dose_value,
                # Same rationale as above for the per-run dose comparison.
                rtol=1e-3,
                atol=0.0,
            ),
            f"Merged dose vs reference: {merged_dose_value:.6e} {reference_dose_value:.6e}",
        )
        and is_ok
    )

    merged_root = merged_sim.get_actor("PhaseSpace").get_output_path()
    reference_root = reference_sim.get_actor("PhaseSpace").get_output_path()
    is_ok = (
        check_phase_space_root(
            reference_root,
            merged_root,
            expected_run_ids=[0, 1],
            run_timing_intervals=run_timing_intervals,
        )
        and is_ok
    )

    print()
    print("Probing failure mode with a missing dose image ...")
    broken_sim = build_simulation(
        paths.output / "merge_context_input_broken",
        run_timing_intervals,
        source_n,
    )
    broken_split_root = gate.jobs_split(
        broken_sim,
        3,
        broken_split_root,
        policy="split_in_time_total",
    )
    broken_run_summary = gate.jobs_run(broken_split_root, backend="local_sequential")
    print(broken_run_summary)
    wait_until_jobs_completed(broken_split_root)

    broken_job_sim = gate.create_sim_from_json(broken_split_root / "job0001" / "simulation.json")
    broken_dose_path = broken_job_sim.get_actor("dose").dose.get_output_path(which=0)
    is_ok = run_failure_probe(broken_split_root, broken_dose_path) and is_ok

    utility.test_ok(is_ok)

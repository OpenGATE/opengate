#!/usr/bin/env python3
"""Exercise mixed-output split-job merging and its failure modes.

This test is the main integration test for the current disk-based merge
workflow. It combines three output families in one split campaign:

- ``SimulationStatisticsActor`` for lightweight JSON/container-backed output
- ``DoseActor`` for standard image-based per-run and merged output
- ``PhaseSpaceActor`` for ROOT-backed output coordinated through the ROOT
  merge path

The test covers three aspects:

1. Planning:
   Inspect the ``MergeContext`` and verify that the split campaign is described
   correctly, including asymmetric run coverage across jobs.
2. Successful merge:
   Run a reference simulation and a split campaign, merge the split outputs,
   and compare standard and ROOT-backed output against the reference.
3. Failure handling:
   Intentionally break expected child output or campaign identity metadata and
   check that merge errors are raised at the right stage with meaningful
   provenance.
"""

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


def get_single_voxel_value_from_actor_output(actor_output, which, item=0):
    return get_single_voxel_value_from_image(
        actor_output.get_data(which=which, item=item)
    )


def get_total_single_voxel_dose_from_actor_output(actor_output, which_values):
    """Return the summed single-voxel dose over the requested output slots."""

    total_dose = 0.0
    for which in which_values:
        total_dose += get_single_voxel_value_from_actor_output(
            actor_output, which=which, item=0
        )
    return total_dose


def build_manual_cumulative_stats_from_per_run(stats_actor):
    """Accumulate the target simulation's per-run stats into a plain dict."""

    stats_output = stats_actor.user_output.stats
    per_run_items = [
        stats_output.data_per_run[run_index].get_data_item_object(0)
        for run_index in sorted(stats_output.data_per_run.keys())
    ]
    manual_counts = {
        "runs": len(per_run_items),
        "events": sum(item.data.events for item in per_run_items),
        "tracks": sum(item.data.tracks for item in per_run_items),
        "steps": sum(item.data.steps for item in per_run_items),
        "duration": sum(item.data.duration for item in per_run_items),
        "track_types": {},
    }
    all_track_names = sorted(
        {
            track_name
            for item in per_run_items
            for track_name in item.data.track_types.keys()
        }
    )
    for track_name in all_track_names:
        manual_counts["track_types"][track_name] = sum(
            int(item.data.track_types.get(track_name, 0)) for item in per_run_items
        )
    return manual_counts


def format_stats_payload(stats_like):
    """Return a compact debug string for statistics-like payloads."""

    return (
        f"runs={stats_like.data.runs}, "
        f"events={stats_like.data.events}, "
        f"tracks={stats_like.data.tracks}, "
        f"steps={stats_like.data.steps}, "
        f"duration={stats_like.data.duration}, "
        f"track_types={dict(stats_like.data.track_types)}"
    )


def format_manual_stats_payload(manual_counts):
    """Return a compact debug string for manual cumulative statistics dicts."""

    return (
        f"runs={manual_counts['runs']}, "
        f"events={manual_counts['events']}, "
        f"tracks={manual_counts['tracks']}, "
        f"steps={manual_counts['steps']}, "
        f"duration={manual_counts['duration']}, "
        f"track_types={manual_counts['track_types']}"
    )


def stats_counts_match_except_runs(stats_item_1, stats_item_2):
    """Compare cumulative statistics while ignoring non-count derived fields."""

    return (
        stats_item_1.data.events == stats_item_2.data.events
        and stats_item_1.data.tracks == stats_item_2.data.tracks
        and stats_item_1.data.steps == stats_item_2.data.steps
    )


def assert_stats_except_runs(stats_actor_1, stats_actor_2, tolerance):
    """Compare stats actors while ignoring the cumulative runs count."""

    counts1 = stats_actor_1.user_output.stats.merged_data.get_data_item_object(0)
    counts2 = stats_actor_2.user_output.stats.merged_data.get_data_item_object(0)
    if isinstance(tolerance, (int, float)):
        tolerance = [tolerance, tolerance, tolerance]

    is_ok = True
    utility.print_test(
        True,
        f"Runs:         {counts1.runs} {counts2.runs} (ignored for cumulative stats consistency)",
    )

    event_d = 0 if counts2.events == 0 else counts1.events / counts2.events * 100 - 100
    track_d = (
        100 if counts2.tracks == 0 else counts1.tracks / counts2.tracks * 100 - 100
    )
    step_d = 100 if counts2.steps == 0 else counts1.steps / counts2.steps * 100 - 100

    b = abs(event_d) <= tolerance[0] * 100
    is_ok = (
        utility.print_test(
            b,
            f"Events:       {counts1.events} {counts2.events} : {event_d:+.2f} %  (tol = {tolerance[0] * 100:.2f} %)",
        )
        and is_ok
    )

    b = abs(track_d) <= tolerance[1] * 100
    is_ok = (
        utility.print_test(
            b,
            f"Tracks:       {counts1.tracks} {counts2.tracks} : {track_d:+.2f} %  (tol = {tolerance[1] * 100:.2f} %)",
        )
        and is_ok
    )

    b = abs(step_d) <= tolerance[2] * 100
    is_ok = (
        utility.print_test(
            b,
            f"Steps:        {counts1.steps} {counts2.steps} : {step_d:+.2f} %  (tol = {tolerance[2] * 100:.2f} %)",
        )
        and is_ok
    )

    return is_ok


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
    source.energy.mono = 10 * MeV
    source.number_of_primaries = source_n
    source.position.type = "disc"
    source.position.radius = 1.0 * nm
    source.position.translation = [0, 0, -9.0 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    sim.physics_manager.global_production_cuts.all = 1.0 * m

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.json"
    stats.keep_data_per_run = True

    # A second statistics actor stores only the cumulative slot. This probes
    # the jobs-merge path for standard outputs that do not keep per-run data.
    stats_cumulative = sim.add_actor("SimulationStatisticsActor", "StatsCumulative")
    stats_cumulative.output_filename = "stats_cumulative.json"
    stats_cumulative.keep_data_per_run = False

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


def wait_until_jobs_completed(split_root, timeout=90):
    """Wait for all jobs in a test campaign to finish.

    The test runs one split campaign and then temporarily corrupts that same
    campaign for failure probes. The timeout is intentionally bounded so a
    genuinely broken campaign fails quickly.
    """

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
        f"Timed out waiting for split jobs to complete in '{split_root}' "
        f"after {timeout} s. Last observed statuses: {last_statuses}"
    )


def check_phase_space_root(
    reference_root, merged_root, expected_run_ids, run_timing_intervals
):
    with uproot.open(reference_root) as reference_file:
        reference_tree = reference_file["PhaseSpace"]
        reference_branches = sorted(reference_tree.keys())
        reference_entries = reference_tree.num_entries
        reference_global_time = reference_tree["GlobalTime"].array(library="np")
        reference_kinetic_energy = reference_tree["KineticEnergy"].array(library="np")

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
    raw_path = None
    moved_raw_path = None
    if broken_output_path.suffix == ".mhd":
        raw_path = broken_output_path.with_suffix(".raw")
        moved_raw_path = moved_output_path.with_suffix(".raw")

    try:
        shutil.move(broken_output_path, moved_output_path)
        if raw_path is not None and raw_path.exists():
            shutil.move(raw_path, moved_raw_path)

        gate.jobs_merge(split_root, to_path=split_root.parent / "broken_merge_output")
    except GateMergeError as error:
        return utility.print_test(
            "dose" in str(error) or "Failed to execute standard merge" in str(error),
            f"Intentional broken-dose merge raises GateMergeError: {error}",
        )
    finally:
        if moved_output_path.exists():
            shutil.move(moved_output_path, broken_output_path)
        if moved_raw_path is not None and moved_raw_path.exists():
            shutil.move(moved_raw_path, raw_path)
    return utility.print_test(
        False,
        "Intentional broken-dose merge should have raised GateMergeError",
    )


def run_missing_stats_probe(split_root, broken_stats_path):
    broken_stats_path = Path(broken_stats_path)
    moved_stats_path = broken_stats_path.with_name(f"broken_{broken_stats_path.name}")

    try:
        shutil.move(broken_stats_path, moved_stats_path)
        gate.jobs_merge(
            split_root, to_path=split_root.parent / "broken_merge_output_stats"
        )
    except GateMergeError as error:
        return utility.print_test(
            "stats" in str(error).lower()
            or "Failed to execute standard merge" in str(error),
            f"Intentional broken-stats merge raises GateMergeError: {error}",
        )
    finally:
        if moved_stats_path.exists():
            shutil.move(moved_stats_path, broken_stats_path)
    return utility.print_test(
        False,
        "Intentional broken-stats merge should have raised GateMergeError",
    )


def run_identity_mismatch_probe(split_root):
    job_metadata_path = Path(split_root) / "job0001" / "job_metadata.json"
    with open(job_metadata_path, "r") as input_file:
        metadata = json.load(input_file)
    original_metadata = dict(metadata)

    try:
        metadata["parent_simulation_id"] = "wrong_parent_simulation_id"
        with open(job_metadata_path, "w") as output_file:
            json.dump(metadata, output_file, indent=2, sort_keys=True)
            output_file.write("\n")

        gate.jobs_merge(split_root, execute=False)
    except Exception as error:
        return utility.print_test(
            "parent simulation id" in str(error).lower()
            or "manifest expects" in str(error).lower(),
            f"Parent/master simulation ID mismatch is detected: {error}",
        )
    finally:
        with open(job_metadata_path, "w") as output_file:
            json.dump(original_metadata, output_file, indent=2, sort_keys=True)
            output_file.write("\n")
    return utility.print_test(
        False,
        "Parent/master simulation ID mismatch should have raised an error",
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
    shutil.rmtree(paths.output / "merged_repeat", ignore_errors=True)
    shutil.rmtree(paths.output / "broken_merge_output", ignore_errors=True)
    shutil.rmtree(paths.output / "broken_merge_output_stats", ignore_errors=True)

    run_timing_intervals = [(0.0 * sec, 1.0 * sec), (2.0 * sec, 5.0 * sec)]
    source_n = [100, 300]

    sim = build_simulation(
        paths.output / "merge_context_input",
        run_timing_intervals,
        source_n,
    )
    split_root = gate.jobs_split(
        simulation=sim,
        number_of_jobs=2,
        campaign_dir=split_root,
        policy="split_in_time_total",
    ).campaign_dir

    merge_manager = gate.jobs_merge(split_root, execute=False)
    merge_context = merge_manager.plan_merge()

    # ------------------------------------------------------------------
    # Merge planning inspection:
    # verify that the flat output inventory and the informative campaign
    # mapping describe the asymmetric split exactly as intended.
    # ------------------------------------------------------------------
    print()
    print("MergeContext pretty dump:")
    print("-------------------------")
    merge_context.print_pretty()

    merge_context_dict = merge_context.to_dict()
    informative_sources = merge_context_dict["informative"]["sources"]
    output_inventory = merge_context_dict["instructive"]["output_inventory"]

    # Check that source records are keyed by the 1-based job indices used in
    # user-facing split/merge summaries.
    utility.print_test(
        sorted(informative_sources.keys()) == [1, 2],
        f"Informative merge-context sources are keyed by job_index: {sorted(informative_sources.keys())}",
    )
    is_ok = sorted(informative_sources.keys()) == [1, 2] and is_ok

    inventory_job_indices = sorted(
        {output_plan["job_index"] for output_plan in output_inventory}
    )
    # Check that the flat output inventory covers both jobs.
    utility.print_test(
        inventory_job_indices == [1, 2],
        f"Flat output inventory covers job_index values: {inventory_job_indices}",
    )
    is_ok = inventory_job_indices == [1, 2] and is_ok

    # Check the total number of actor-output plans produced by the mixed-output
    # simulation: two stats outputs, four dose outputs, and one ROOT output per job.
    utility.print_test(
        len(output_inventory) == 14,
        f"Flat output inventory contains one entry per job and actor output: {len(output_inventory)}",
    )
    is_ok = len(output_inventory) == 14 and is_ok

    # Check that job0001 bridges the original run boundary and therefore maps
    # two local runs back to original runs 0 and 1.
    utility.print_test(
        informative_sources[1]["local_to_original_run_map"] == [0, 1],
        f"job0001 local-to-original run map: {informative_sources[1]['local_to_original_run_map']}",
    )
    is_ok = informative_sources[1]["local_to_original_run_map"] == [0, 1] and is_ok

    # Check that job0002 contributes only to original run 1.
    utility.print_test(
        informative_sources[2]["local_to_original_run_map"] == [1],
        f"job0002 local-to-original run map: {informative_sources[2]['local_to_original_run_map']}",
    )
    is_ok = informative_sources[2]["local_to_original_run_map"] == [1] and is_ok

    # Check the asymmetric split multiplicity: one child contributes to
    # original run 0, while two children contribute to original run 1.
    utility.print_test(
        merge_context_dict["informative"]["number_of_children_per_original_run"]
        == {0: 1, 1: 2},
        f"Original-run contributor multiplicities: {merge_context_dict['informative']['number_of_children_per_original_run']}",
    )
    is_ok = (
        merge_context_dict["informative"]["number_of_children_per_original_run"]
        == {0: 1, 1: 2}
        and is_ok
    )

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
    stats_cumulative_plan_job1 = next(
        output_plan
        for output_plan in output_inventory
        if output_plan["job_index"] == 1
        and output_plan["actor_name"] == "StatsCumulative"
        and output_plan["output_name"] == "stats"
    )

    # Check that statistics output is routed to the standard merge coordinator.
    utility.print_test(
        stats_plan_job1["merge_coordinator"] == "standard",
        f"Statistics output merge coordinator: {stats_plan_job1['merge_coordinator']}",
    )
    is_ok = stats_plan_job1["merge_coordinator"] == "standard" and is_ok

    # Check that dose image output is also routed to the standard coordinator.
    utility.print_test(
        dose_plan_job1["merge_coordinator"] == "standard",
        f"Dose output merge coordinator: {dose_plan_job1['merge_coordinator']}",
    )
    is_ok = dose_plan_job1["merge_coordinator"] == "standard" and is_ok

    # Check that ROOT output is delegated to the dedicated ROOT coordinator.
    utility.print_test(
        phsp_plan_job1["merge_coordinator"] == "root",
        f"Phase-space output merge coordinator: {phsp_plan_job1['merge_coordinator']}",
    )
    is_ok = phsp_plan_job1["merge_coordinator"] == "root" and is_ok

    # Check that the cumulative-only statistics output is still routed through
    # the standard merge coordinator.
    utility.print_test(
        stats_cumulative_plan_job1["merge_coordinator"] == "standard",
        f"Cumulative-only statistics output merge coordinator: {stats_cumulative_plan_job1['merge_coordinator']}",
    )
    is_ok = stats_cumulative_plan_job1["merge_coordinator"] == "standard" and is_ok

    # Check that the statistics actor plans per-run output for both local runs
    # of job0001 plus one merged output slot.
    utility.print_test(
        [
            contribution["source_scope"]
            for contribution in stats_plan_job1["contributions"]
        ]
        == [0, 1, "merged"],
        f"job0001 statistics source scopes: {[contribution['source_scope'] for contribution in stats_plan_job1['contributions']]}",
    )
    is_ok = [
        contribution["source_scope"]
        for contribution in stats_plan_job1["contributions"]
    ] == [0, 1, "merged"] and is_ok

    # Check that the merge plan resolves the concrete filenames that the
    # primary dose item will contribute from job0001.
    utility.print_test(
        [
            Path(contribution["output_path"]).name
            for contribution in dose_plan_job1["contributions"]
            if contribution["item_identifier"] == 0
        ]
        == ["dose-run0.mhd", "dose-run1.mhd", "dose.mhd"],
        f"job0001 resolved planned dose output paths: {[Path(contribution['output_path']).name for contribution in dose_plan_job1['contributions'] if contribution['item_identifier'] == 0]}",
    )
    is_ok = [
        Path(contribution["output_path"]).name
        for contribution in dose_plan_job1["contributions"]
        if contribution["item_identifier"] == 0
    ] == ["dose-run0.mhd", "dose-run1.mhd", "dose.mhd"] and is_ok

    # Check that the phase-space actor contributes one ROOT stream per local
    # run present in job0001.
    utility.print_test(
        len(phsp_plan_job1["contributions"]) == 2,
        f"job0001 planned phase-space contributions: {len(phsp_plan_job1['contributions'])}",
    )
    is_ok = len(phsp_plan_job1["contributions"]) == 2 and is_ok

    # Check that the cumulative-only statistics actor contributes only its
    # cumulative slot and no per-run payload.
    utility.print_test(
        [
            contribution["source_scope"]
            for contribution in stats_cumulative_plan_job1["contributions"]
        ]
        == ["merged"],
        f"job0001 cumulative-only statistics source scopes: {[contribution['source_scope'] for contribution in stats_cumulative_plan_job1['contributions']]}",
    )
    is_ok = [
        contribution["source_scope"]
        for contribution in stats_cumulative_plan_job1["contributions"]
    ] == ["merged"] and is_ok

    # ------------------------------------------------------------------
    # Successful merge path:
    # compare the merged campaign against a non-split reference simulation.
    # This validates the merge lifecycle, per-run image output, merged image
    # output, and ROOT output ordering/remapping.
    # ------------------------------------------------------------------
    print()
    print("Running reference simulation ...")
    reference_sim = build_simulation(
        paths.output / "reference",
        run_timing_intervals,
        source_n,
    )
    reference_sim.run(start_new_process=True)

    print("Running split jobs sequentially ...")
    run_summary = gate.jobs_run(
        split_root,
        backend="local_sequential",
        detach=False,
    )
    print(run_summary)
    wait_until_jobs_completed(split_root)

    print("Merging split jobs ...")
    merge_manager = gate.jobs_merge(
        split_root, to_path=paths.output / "merged", execute=True
    )
    merged_sim = merge_manager.master_simulation

    # Check that the merged simulation writes into the explicit merge target
    # folder instead of reusing the split campaign folder.
    utility.print_test(
        merged_sim.output_dir == paths.output / "merged",
        f"Merged simulation output dir: {merged_sim.output_dir}",
    )
    is_ok = (merged_sim.output_dir == paths.output / "merged") and is_ok

    # Check that the merge lifecycle completed all three stages successfully.
    utility.print_test(
        merge_manager.merge_planned
        and merge_manager.merge_executed
        and merge_manager.merge_finalized,
        f"Merge lifecycle flags: planned={merge_manager.merge_planned} executed={merge_manager.merge_executed} finalized={merge_manager.merge_finalized}",
    )
    is_ok = (
        merge_manager.merge_planned
        and merge_manager.merge_executed
        and merge_manager.merge_finalized
        and is_ok
    )

    is_ok = (
        assert_stats_except_runs(
            merged_sim.get_actor("Stats"),
            reference_sim.get_actor("Stats"),
            tolerance=[0, 0.10, 0.10],
        )
        and is_ok
    )

    merged_stats_output = merged_sim.get_actor("Stats").user_output.stats
    merged_stats_item = merged_stats_output.merged_data.get_data_item_object(0)
    manual_stats = build_manual_cumulative_stats_from_per_run(
        merged_sim.get_actor("Stats")
    )
    # Check that the target cumulative stats slot created by jobs merge equals
    # a manual accumulation of the target's own per-run stats slots for the
    # primary count entries. Duration and other derived timing fields are not
    # asserted here because this check is about accumulation of scored counts.
    is_ok = (
        utility.print_test(
            merged_stats_item.data.events == manual_stats["events"]
            and merged_stats_item.data.tracks == manual_stats["tracks"]
            and merged_stats_item.data.steps == manual_stats["steps"]
            and dict(merged_stats_item.data.track_types) == manual_stats["track_types"],
            "Target cumulative stats equal manual accumulation of target per-run stats except for runs"
            f" | merged: {format_stats_payload(merged_stats_item)}"
            f" | manual: {format_manual_stats_payload(manual_stats)}",
        )
        and is_ok
    )

    merged_stats_cumulative_output = merged_sim.get_actor(
        "StatsCumulative"
    ).user_output.stats
    merged_stats_cumulative_item = (
        merged_stats_cumulative_output.merged_data.get_data_item_object(0)
    )
    # Check that the cumulative-only statistics actor received cumulative data
    # through jobs merge even though it kept no per-run slots.
    is_ok = (
        utility.print_test(
            len(merged_stats_cumulative_output.data_per_run) == 0,
            "Cumulative-only statistics actor keeps no per-run data after merge",
        )
        and is_ok
    )
    # Check that the cumulative-only statistics output matches the cumulative
    # result of the per-run statistics actor for the primary count entries,
    # again ignoring the unreliable runs count and non-count timing details.
    is_ok = (
        utility.print_test(
            stats_counts_match_except_runs(
                merged_stats_cumulative_item, merged_stats_item
            ),
            "Cumulative-only statistics output matches the per-run statistics actor cumulative output except for runs"
            f" | cumulative-only: {format_stats_payload(merged_stats_cumulative_item)}"
            f" | per-run actor cumulative: {format_stats_payload(merged_stats_item)}",
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
        # Check each per-run merged dose image against the corresponding
        # reference per-run dose image.
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
    # Check the final merged dose image against the merged reference dose image.
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

    merged_per_run_dose_sum_on_disk = sum(
        read_single_voxel_value(merged_dose.dose.get_output_path(which=run_index))
        for run_index in range(len(run_timing_intervals))
    )
    # Check internal merged-dose consistency on disk: the cumulative merged
    # dose map should equal the sum of the merged per-run dose maps.
    is_ok = (
        utility.print_test(
            np.isclose(
                merged_per_run_dose_sum_on_disk,
                merged_dose_value,
                rtol=1e-3,
                atol=0.0,
            ),
            f"Merged cumulative dose on disk equals sum of merged per-run dose maps: {merged_per_run_dose_sum_on_disk:.6e} {merged_dose_value:.6e}",
        )
        and is_ok
    )

    reference_per_run_dose_sum_on_disk = sum(
        read_single_voxel_value(reference_dose.dose.get_output_path(which=run_index))
        for run_index in range(len(run_timing_intervals))
    )
    # Check the same cumulative-versus-per-run contract on the unsplit
    # reference simulation so the test probes both the general actor-output
    # behavior and the split-merge behavior under the same criterion.
    is_ok = (
        utility.print_test(
            np.isclose(
                reference_per_run_dose_sum_on_disk,
                reference_dose_value,
                rtol=1e-3,
                atol=0.0,
            ),
            f"Reference cumulative dose on disk equals sum of reference per-run dose maps: {reference_per_run_dose_sum_on_disk:.6e} {reference_dose_value:.6e}",
        )
        and is_ok
    )

    merged_in_memory_per_run_dose_sum = get_total_single_voxel_dose_from_actor_output(
        merged_dose.dose, range(len(run_timing_intervals))
    )
    merged_in_memory_cumulative_dose = get_single_voxel_value_from_actor_output(
        merged_dose.dose, which="merged", item=0
    )
    # Check the same contract in memory on the merged target actor output.
    is_ok = (
        utility.print_test(
            np.isclose(
                merged_in_memory_per_run_dose_sum,
                merged_in_memory_cumulative_dose,
                rtol=1e-3,
                atol=0.0,
            ),
            f"Merged cumulative dose in memory equals sum of merged per-run dose maps: {merged_in_memory_per_run_dose_sum:.6e} {merged_in_memory_cumulative_dose:.6e}",
        )
        and is_ok
    )

    merged_root = merged_sim.get_actor("PhaseSpace").get_output_path()
    reference_root = reference_sim.get_actor("PhaseSpace").get_output_path()
    # Check ROOT consistency: the merged file should preserve run assignment,
    # ordering, and branch structure relative to the reference simulation.
    is_ok = (
        check_phase_space_root(
            reference_root,
            merged_root,
            expected_run_ids=[0, 1],
            run_timing_intervals=run_timing_intervals,
        )
        and is_ok
    )

    # Re-run the merge into the same target folder and make sure the produced
    # merged output stays numerically stable. This guards against accidental
    # append-style behavior or non-idempotent overwrite logic.
    print()
    print("Repeating merge into the same target folder ...")
    repeat_merge_manager = gate.jobs_merge(
        split_root, to_path=paths.output / "merged", execute=True
    )
    repeated_merged_sim = repeat_merge_manager.master_simulation
    repeated_merged_dose_value = read_single_voxel_value(
        repeated_merged_sim.get_actor("dose").dose.get_output_path(which="merged")
    )
    # Check repeated-merge stability: re-merging into the same target folder
    # should not perturb the resulting merged dose.
    is_ok = (
        utility.print_test(
            np.isclose(
                repeated_merged_dose_value,
                merged_dose_value,
                rtol=1e-3,
                atol=0.0,
            ),
            f"Repeated merge into existing target folder is stable: {repeated_merged_dose_value:.6e} {merged_dose_value:.6e}",
        )
        and is_ok
    )

    # ------------------------------------------------------------------
    # Failure handling:
    # deliberately corrupt the completed split campaign in place, then restore
    # the moved files/metadata inside each probe. This keeps the failure probes
    # realistic and independent without rerunning additional simulations.
    # ------------------------------------------------------------------
    print()
    print("Probing failure mode with a missing dose image ...")
    broken_job_sim = gate.create_sim_from_json(
        split_root / "job0001" / "simulation.json"
    )
    broken_dose_path = broken_job_sim.get_actor("dose").dose.get_output_path(
        which="merged"
    )
    # Check missing-image failure handling at the standard image-output level.
    # The cumulative file is always part of this merge workflow, while per-run
    # files can be legitimately absent if a child run has no scored payload.
    is_ok = run_failure_probe(split_root, broken_dose_path) and is_ok

    print()
    print("Probing failure mode with a missing stats JSON ...")
    broken_stats_job_sim = gate.create_sim_from_json(
        split_root / "job0001" / "simulation.json"
    )
    broken_stats_job_path = broken_stats_job_sim.get_actor(
        "Stats"
    ).user_output.stats.get_output_path(which="merged")
    # Check missing-JSON failure handling at the lightweight stats-output level.
    # The cumulative stats JSON is always part of this merge workflow, unlike a
    # sparse per-run stats file.
    is_ok = run_missing_stats_probe(split_root, broken_stats_job_path) and is_ok

    print()
    print("Probing parent/master simulation ID mismatch ...")
    # Check that a corrupted child parent/master simulation ID is detected
    # before merge planning can proceed.
    is_ok = run_identity_mismatch_probe(split_root) and is_ok

    utility.test_ok(is_ok)

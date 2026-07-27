#!/usr/bin/env python3
"""Exercise ROOT-only split-job merging for PhaseSpaceActor branch variants.

This test complements ``test113_jobs_merge_context.py`` by focusing only on
phase-space ROOT output. It covers three related concerns in one place:

1. asymmetric multi-run split structure under ``split_in_time_total``
2. ROOT merge when ``EventID`` is not requested but ``keep_data_per_run=True``
3. ROOT merge when neither ``EventID`` nor ``keep_data_per_run`` is enabled

The first configuration checks that GATE auto-injects ``RunID`` while leaving
``EventID`` absent. The second configuration checks that merge degrades to
ordered concatenation with no synthetic identity branches.
"""

import shutil
import time
from pathlib import Path

import numpy as np
import opengate as gate
import uproot
from opengate.serialization import load_json_with_retry
from opengate.tests import utility


def build_phsp_only_simulation(
    output_dir,
    run_timing_intervals,
    keep_data_per_run,
    random_seed,
):
    """Build a small ROOT-only simulation for split/merge tests."""

    sim = gate.Simulation()
    sim.output_dir = Path(output_dir)
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = random_seed

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    sphere = sim.add_volume("Sphere", "phase_space_plane")
    sphere.material = "G4_AIR"
    sphere.rmax = 20 * cm

    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.type = "gauss"
    source.energy.mono = 10 * keV
    source.energy.sigma_gauss = source.energy.mono * 0.01
    source.position.type = "point"
    source.direction.type = "iso"
    source.activity = 1000 * Bq

    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = sphere
    phsp.steps_to_store = "first"
    phsp.output_filename = "test113_phsp.root"
    phsp.attributes = ["GlobalTime", "KineticEnergy"]
    phsp.keep_data_per_run = keep_data_per_run

    sim.run_timing_intervals = run_timing_intervals
    return sim, phsp


def wait_until_jobs_completed(split_root, timeout=60):
    """Wait until all child jobs report completed status."""

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
            return manifest
        time.sleep(0.5)
    raise RuntimeError(
        f"Timed out waiting for split jobs to complete. Last observed statuses: {last_statuses}"
    )


def check_merge_context_asymmetric_split(merge_context, expected_multiplicity):
    """Validate the run-coverage pattern induced by total-time splitting."""

    merge_context_dict = merge_context.to_dict()
    source_map = merge_context_dict["informative"]["sources"]
    multiplicity = merge_context_dict["informative"][
        "number_of_children_per_original_run"
    ]
    is_ok = True

    # The planning context should expose all three child jobs by their 1-based
    # job indices.
    is_ok = (
        utility.print_test(
            sorted(source_map.keys()) == [1, 2, 3],
            f"Merge-context source keys for asymmetric split: {sorted(source_map.keys())}",
        )
        and is_ok
    )

    # With original intervals [(0, 1), (2, 5)] and three equal total-time
    # chunks, only the later original run is bridged multiple times.
    is_ok = (
        utility.print_test(
            multiplicity == expected_multiplicity,
            f"Asymmetric original-run contributor multiplicity: {multiplicity}",
        )
        and is_ok
    )
    return is_ok


def check_child_branch_contract(
    split_root, expect_runid, expect_eventid, expect_keep_data_per_run
):
    """Inspect child simulations and child ROOT trees for the expected schema."""

    manifest = load_json_with_retry(split_root / "jobs_manifest.json")
    is_ok = True
    for job in manifest["jobs"]:
        job_folder = split_root / job["folder_name"]
        child_sim = gate.create_sim_from_json(job_folder / "simulation.json")
        child_phsp = child_sim.get_actor("PhaseSpace")
        with uproot.open(job_folder / "test113_phsp.root") as root_file:
            branch_names = sorted(root_file["PhaseSpace"].keys())

        # Rehydrated actor configuration should reflect whether RunID had to be
        # auto-injected during split preparation.
        is_ok = (
            utility.print_test(
                child_phsp.keep_data_per_run == expect_keep_data_per_run,
                f"{job['folder_name']} keep_data_per_run after rehydration: {child_phsp.keep_data_per_run}",
            )
            and is_ok
        )
        # Child ROOT files should contain RunID only when per-run preservation
        # is requested.
        is_ok = (
            utility.print_test(
                ("RunID" in branch_names) == expect_runid,
                f"{job['folder_name']} ROOT tree RunID presence: {'RunID' in branch_names}",
            )
            and is_ok
        )
        # EventID should stay absent because the user did not request it in
        # either variant covered by this test.
        is_ok = (
            utility.print_test(
                ("EventID" in branch_names) == expect_eventid,
                f"{job['folder_name']} ROOT tree EventID presence: {'EventID' in branch_names}",
            )
            and is_ok
        )
    return is_ok


def check_merged_root(
    reference_root,
    merged_root,
    run_timing_intervals,
    expect_runid,
    expect_eventid,
    time_order_tolerance,
):
    """Compare merged ROOT output against reference and branch expectations."""

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
        merged_run_ids = (
            merged_tree["RunID"].array(library="np")
            if "RunID" in merged_branches
            else None
        )

    is_ok = True

    # Merged and reference trees should expose the same branches for a given
    # actor configuration.
    is_ok = (
        utility.print_test(
            merged_branches == reference_branches,
            f"Merged PhaseSpace branches: {merged_branches}",
        )
        and is_ok
    )

    # Split/merge should preserve the ROOT entry statistics up to ordinary
    # stochastic fluctuations of an activity-driven source. Exact equality is
    # too strict here because the reference and split campaigns are sampled
    # independently.
    is_ok = (
        utility.print_test(
            np.isclose(
                merged_entries,
                reference_entries,
                rtol=0.05,
                atol=0.0,
            ),
            f"Merged PhaseSpace entries vs reference: {merged_entries} {reference_entries}",
        )
        and is_ok
    )

    # Even without EventID, merging should preserve chronological order up to a
    # small tolerance. Two primaries emitted very close in time can still be
    # recorded in slightly inverted order after stochastic transport.
    min_time_diff = (
        float(np.min(np.diff(merged_global_time)))
        if len(merged_global_time) > 1
        else 0.0
    )
    is_ok = (
        utility.print_test(
            min_time_diff >= -time_order_tolerance,
            "Merged GlobalTime values do not decrease by more than the allowed "
            f"tolerance ({time_order_tolerance / gate.g4_units.ns:.3f} ns). "
            f"Most negative time step: {min_time_diff / gate.g4_units.ns:.6f} ns. "
            + format_time_order_debug(merged_global_time),
        )
        and is_ok
    )

    # The merged energy distribution should remain statistically consistent
    # with the non-split reference simulation.
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

    # RunID should be present only in the keep_data_per_run case.
    is_ok = (
        utility.print_test(
            ("RunID" in merged_branches) == expect_runid,
            f"Merged ROOT RunID presence: {'RunID' in merged_branches}",
        )
        and is_ok
    )

    # EventID should stay absent in both variants of this test.
    is_ok = (
        utility.print_test(
            ("EventID" in merged_branches) == expect_eventid,
            f"Merged ROOT EventID presence: {'EventID' in merged_branches}",
        )
        and is_ok
    )

    if expect_runid:
        expected_run_ids = np.arange(len(run_timing_intervals))
        # If RunID is present, it should be remapped back to the original run
        # indices of the master simulation.
        is_ok = (
            utility.print_test(
                np.array_equal(np.unique(merged_run_ids), expected_run_ids),
                f"Merged RunID values: {np.unique(merged_run_ids).tolist()}",
            )
            and is_ok
        )
        for run_id, run_interval in enumerate(run_timing_intervals):
            run_times = merged_global_time[merged_run_ids == run_id]
            # Each RunID block should stay inside the original run interval it
            # maps back to.
            is_ok = (
                utility.print_test(
                    run_interval[0] <= np.min(run_times) <= run_interval[1]
                    and run_interval[0] <= np.max(run_times) <= run_interval[1],
                    f"RunID {run_id} GlobalTime range stays within [{run_interval[0]/gate.g4_units.s:.6f}, {run_interval[1]/gate.g4_units.s:.6f}] s",
                )
                and is_ok
            )
    else:
        # Without RunID, we can still check that the merged stream stays inside
        # the overall simulation timing extent.
        is_ok = (
            utility.print_test(
                run_timing_intervals[0][0] <= np.min(merged_global_time)
                and np.max(merged_global_time) <= run_timing_intervals[-1][1],
                f"Merged GlobalTime range stays within overall simulation interval [{run_timing_intervals[0][0]/gate.g4_units.s:.6f}, {run_timing_intervals[-1][1]/gate.g4_units.s:.6f}] s",
            )
            and is_ok
        )
    return is_ok


def format_time_order_debug(global_times, window_radius=3):
    """Return a short debug string around the first non-monotonic time step."""

    diffs = np.diff(global_times)
    bad_indices = np.where(diffs < 0)[0]
    if len(bad_indices) == 0:
        return "GlobalTime sequence is monotonic."

    first_bad = int(bad_indices[0])
    start = max(0, first_bad - window_radius)
    stop = min(len(global_times), first_bad + window_radius + 2)
    segment = global_times[start:stop]
    segment_as_seconds = [float(value / gate.g4_units.s) for value in segment]
    return (
        f"first decreasing pair at indices {first_bad}->{first_bad + 1}; "
        f"local GlobalTime segment in seconds: {segment_as_seconds}"
    )


def run_case(paths, case_name, keep_data_per_run, expect_runid, expect_eventid):
    """Run one ROOT-only merge scenario and validate its branch contract."""

    sec = gate.g4_units.s
    ns = gate.g4_units.ns
    run_timing_intervals = [(0.0 * sec, 1.0 * sec), (2.0 * sec, 5.0 * sec)]
    split_root = paths.output / case_name / "split"
    reference_output = paths.output / case_name / "reference"
    merged_output = paths.output / case_name / "merged"

    shutil.rmtree(paths.output / case_name, ignore_errors=True)

    sim, phsp = build_phsp_only_simulation(
        split_root.parent / "master_input",
        run_timing_intervals,
        keep_data_per_run=keep_data_per_run,
        random_seed=123456,
    )

    # The user-facing attribute list intentionally omits EventID in both
    # variants. RunID may later be auto-injected only if keep_data_per_run=True.
    is_ok = utility.print_test(
        "EventID" not in phsp.attributes,
        f"{case_name} user-facing attributes before resolve: {phsp.attributes}",
    )
    is_ok = (
        utility.print_test(
            "RunID" not in phsp.attributes,
            f"{case_name} user-facing attributes do not request RunID explicitly",
        )
        and is_ok
    )

    split_root = gate.jobs_split(
        simulation=sim,
        number_of_jobs=3,
        jobs_root_dir=split_root,
        policy="split_in_time_total",
    )

    merge_manager = gate.jobs_merge(split_root, execute=False)
    merge_context = merge_manager.plan_merge()

    # The asymmetric total-time split itself is part of what this test wants to
    # exercise, independent of the exact ROOT branch variant.
    is_ok = (
        check_merge_context_asymmetric_split(
            merge_context, expected_multiplicity={0: 1, 1: 3}
        )
        and is_ok
    )

    reference_sim, _ = build_phsp_only_simulation(
        reference_output,
        run_timing_intervals,
        keep_data_per_run=keep_data_per_run,
        random_seed=123456,
    )
    reference_sim.run(start_new_process=True)

    run_summary = gate.jobs_run(split_root, backend="local_sequential")
    is_ok = (
        utility.print_test(
            run_summary["submitted_jobs"] == 3,
            f"{case_name} submitted split jobs: {run_summary}",
        )
        and is_ok
    )
    wait_until_jobs_completed(split_root)

    # Child simulations and child ROOT files should reflect the expected branch
    # contract after split preparation and execution.
    is_ok = (
        check_child_branch_contract(
            split_root,
            expect_runid=expect_runid,
            expect_eventid=expect_eventid,
            expect_keep_data_per_run=keep_data_per_run,
        )
        and is_ok
    )

    merged_manager = gate.jobs_merge(split_root, to_path=merged_output, execute=True)
    merged_root = merged_manager.master_simulation.get_actor(
        "PhaseSpace"
    ).get_output_path()
    reference_root = reference_sim.get_actor("PhaseSpace").get_output_path()

    # The merged ROOT file should obey the same branch contract as the child
    # files and remain statistically consistent with the reference simulation.
    is_ok = (
        check_merged_root(
            reference_root,
            merged_root,
            run_timing_intervals,
            expect_runid=expect_runid,
            expect_eventid=expect_eventid,
            time_order_tolerance=1.0 * ns,
        )
        and is_ok
    )

    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test113")
    is_ok = True

    print()
    print("Case 1: keep_data_per_run=True, no EventID requested")
    is_ok = (
        run_case(
            paths,
            case_name="phsp_keep_data_per_run_no_eventid",
            keep_data_per_run=True,
            expect_runid=True,
            expect_eventid=False,
        )
        and is_ok
    )

    print()
    print("Case 2: keep_data_per_run=False, no EventID requested")
    is_ok = (
        run_case(
            paths,
            case_name="phsp_no_eventid_no_keep_data_per_run",
            keep_data_per_run=False,
            expect_runid=False,
            expect_eventid=False,
        )
        and is_ok
    )

    utility.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import shutil
from pathlib import Path

import awkward as ak
import matplotlib.pyplot as plt
import numpy as np
import opengate as gate
import uproot
from opengate.contrib.root_helpers import (
    root_tree_get_branch_data,
    root_tree_get_branch_types,
    root_write_tree,
)
from opengate.tests import utility
from opengate.tests.src.geometry.test009_voxels_dynamic_helpers import (
    wait_for_completed_jobs,
)


def pretty_json(data):
    return json.dumps(data, indent=2, sort_keys=True)


def build_tac_activity_simulation(output_dir):
    sim = gate.Simulation()

    m = gate.g4_units.m
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    kBq = 1e3 * Bq
    sec = gate.g4_units.s
    keV = gate.g4_units.keV

    sim.visu = False
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.number_of_threads = 1
    sim.random_seed = 987654321
    sim.output_dir = Path(output_dir)
    sim.user_info.running_verbose_level = 0  # gate.logger.EVENT

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.position.type = "sphere"
    source.position.radius = 1 * nm
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.energy.mono = 140 * keV

    starting_activity = 100 * kBq / sim.number_of_threads
    half_life = 2 * sec
    times = np.linspace(1, 6, num=500, endpoint=True) * sec
    decay = np.log(2) / half_life
    activities = [starting_activity * np.exp(-decay * t) for t in times]
    source.tac_times = times
    source.tac_activities = activities

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"
    stats.track_types_flag = True

    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attributes = ["GlobalTime"]
    phsp.steps_to_store = "exiting"
    phsp.output_filename = "test052_tac.root"

    # Keep the original runtime gap from the reference test.
    sim.run_timing_intervals = [[0, 2.9 * sec], [3 * sec, 7 * sec]]
    return sim, phsp, half_life


def merge_phase_space_root_from_jobs(
    job_folders,
    output_path,
    root_filename="test052_tac.root",
    tree_name="phsp",
):
    merged_branch_data = {}
    for job_folder in job_folders:
        root_path = Path(job_folder) / root_filename
        if not root_path.exists():
            print(
                f"{Path(job_folder).name}: no {root_filename} written, treating as a valid zero-event job."
            )
            continue
        with uproot.open(root_path) as root_file:
            tree = root_file[tree_name]
            branch_data = root_tree_get_branch_data(tree, library="ak")
            for branch_name, values in branch_data.items():
                merged_branch_data.setdefault(branch_name, []).append(values)

    if len(merged_branch_data) == 0:
        raise RuntimeError("No phase-space ROOT data found in any split job folder.")

    concatenated_branch_data = {
        branch_name: ak.concatenate(chunks) if len(chunks) > 1 else chunks[0]
        for branch_name, chunks in merged_branch_data.items()
    }
    branch_types = root_tree_get_branch_types(concatenated_branch_data)
    with uproot.recreate(output_path) as output_file:
        root_write_tree(output_file, tree_name, branch_types, concatenated_branch_data)
    return output_path


def check_missing_root_files_are_zero_event_jobs(
    job_folders, root_filename="test052_tac.root"
):
    is_ok = True
    for job_folder in job_folders:
        root_path = Path(job_folder) / root_filename
        if root_path.exists():
            continue
        stats = utility.read_stats_file(Path(job_folder) / "stats.txt")
        print(
            f"stats.user_output.stats.merged_data.events = {stats.user_output.stats.merged_data.events}"
        )
        is_ok = (
            # no ROOT file is consistent in case there are no events -> check this
            # there is always at least a geantino (see GateSourceManager), so 1 means effectively 0
            utility.print_test(
                stats.user_output.stats.merged_data.events <= 1,
                f"{Path(job_folder).name} missing {root_filename} and reports zero events",
            )
            and is_ok
        )
    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test052")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True

    sec = gate.g4_units.s
    split_path = paths.output / "split_campaign_pool"
    split_sim, _, half_life = build_tac_activity_simulation(
        split_path.parent / f"{split_path.name}_master_input"
    )

    split_root = gate.jobs_split(
        split_sim,
        8,
        split_path,
        policy="split_in_time_total",
    )
    summary = gate.jobs_run(
        split_root,
        backend="local_pool",
        backend_options={
            "n_workers": 8,
            "start_method": "spawn",
            "maxtasksperchild": 1,
        },
    )
    is_ok = (
        utility.print_test(
            summary["submitted_jobs"] == 8,
            f"local_pool split summary:\n{pretty_json(summary)}",
        )
        and is_ok
    )

    status_data = wait_for_completed_jobs(split_root, expected_count=8)
    job_folders = [split_root / job["folder_name"] for job in status_data["jobs"]]
    is_ok = check_missing_root_files_are_zero_event_jobs(job_folders) and is_ok

    merged_root = paths.output / "test052_tac_merged.root"
    merge_phase_space_root_from_jobs(job_folders, merged_root)

    root_data, _ = utility.open_root_as_np(merged_root, "phsp")
    event_times_seconds = root_data["GlobalTime"] / sec
    print(f"Number of merged events: {len(event_times_seconds)}")

    fitted_half_life_seconds, fit_xx, fit_yy = utility.fit_exponential_decay(
        event_times_seconds, 0, 7
    )
    reference_half_life_seconds = half_life / sec
    relative_difference = abs(fitted_half_life_seconds - reference_half_life_seconds)
    relative_difference /= reference_half_life_seconds
    tolerance = 0.05
    is_ok = (
        utility.print_test(
            relative_difference < tolerance,
            f"Half life {reference_half_life_seconds:.2f} s vs {fitted_half_life_seconds:.2f} s : "
            f"{relative_difference * 100:.2f}%",
        )
        and is_ok
    )

    figure, axis = plt.subplots(1, 1, figsize=(25, 10))
    utility.plot_hist(axis, event_times_seconds, "Merged events times")
    axis.plot(fit_xx, fit_yy, label="fit")
    axis.legend()

    figure_path = paths.output / "test052_tac_times_jobs_split.png"
    plt.savefig(figure_path)
    print(f"Plot in {figure_path}")

    utility.test_ok(is_ok)

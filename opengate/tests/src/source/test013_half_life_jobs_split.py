#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import shutil
from pathlib import Path

import awkward as ak
import numpy as np
import opengate as gate
import uproot
from opengate.actors.filters import GateFilterBuilder
from opengate.actors.simulation_stats_helpers import sum_stats, write_stats
from opengate.contrib.root_helpers import (
    root_tree_get_branch_data,
    root_tree_get_branch_types,
    root_write_tree,
)
from opengate.sources.utility import get_rad_yield
from opengate.tests import utility
from opengate.tests.src.geometry.test009_voxels_dynamic_helpers import (
    wait_for_completed_jobs,
)


def pretty_json(data):
    return json.dumps(data, indent=2, sort_keys=True)


def build_half_life_simulation(output_dir):
    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.visu = False
    sim.check_volumes_overlap = False
    sim.output_dir = Path(output_dir)
    sim.random_seed = 42

    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s

    sim.world.size = [1 * m, 1 * m, 1 * m]

    waterbox_1 = sim.add_volume("Box", "waterbox1")
    waterbox_1.size = [20 * cm, 20 * cm, 20 * cm]
    waterbox_1.translation = [-20 * cm, 0, 0]

    waterbox_2 = sim.add_volume("Box", "waterbox2")
    waterbox_2.size = [20 * cm, 20 * cm, 20 * cm]
    waterbox_2.translation = [20 * cm, 0, 0]

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.global_production_cuts.all = 0.1 * mm

    activity = 10 * Bq
    half_life = 6586.26 * sec

    ion_source = sim.add_source("GenericSource", "ion_source")
    ion_source.attached_to = waterbox_1.name
    ion_source.particle = "ion 9 18"
    ion_source.position.type = "sphere"
    ion_source.position.radius = 10 * mm
    ion_source.direction.type = "iso"
    ion_source.energy.type = "mono"
    ion_source.energy.mono = 0
    ion_source.half_life = half_life
    ion_source.activity = activity

    beta_source = sim.add_source("GenericSource", "beta+_source")
    beta_source.attached_to = waterbox_2.name
    beta_source.particle = "e+"
    beta_source.position.type = "sphere"
    beta_source.position.radius = 10 * mm
    beta_source.energy.type = "F18"
    beta_source.direction.type = "iso"
    beta_source.half_life = half_life
    beta_source.activity = activity * get_rad_yield("F18")

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"
    stats.track_types_flag = True

    particle_filter_builder = GateFilterBuilder()
    phsp_attributes = [
        "KineticEnergy",
        "LocalTime",
        "GlobalTime",
        "TrackProperTime",
        "TimeFromBeginOfEvent",
    ]

    phsp_ion = sim.add_actor("PhaseSpaceActor", "phsp_ion")
    phsp_ion.attached_to = waterbox_1.name
    phsp_ion.attributes = phsp_attributes
    phsp_ion.output_filename = "test013_decay_ion.root"
    phsp_ion.steps_to_store = "first"
    phsp_ion.filter = particle_filter_builder.ParticleName == "e+"

    phsp_beta = sim.add_actor("PhaseSpaceActor", "phsp_beta")
    phsp_beta.attached_to = waterbox_2.name
    phsp_beta.attributes = phsp_attributes
    phsp_beta.output_filename = "test013_decay_beta_plus.root"
    phsp_beta.steps_to_store = "first"
    phsp_beta.filter = particle_filter_builder.ParticleName == "e+"

    sim.run_timing_intervals = [[0, 109 * 60 * sec]]
    return sim, stats, phsp_ion, phsp_beta


def merge_stats_from_jobs(job_folders, output_path):
    merged_stats = None
    for job_folder in job_folders:
        job_stats = utility.read_stats_file(Path(job_folder) / "stats.txt")
        merged_stats = (
            job_stats if merged_stats is None else sum_stats(merged_stats, job_stats)
        )

    merged_stats.counts.runs = 1
    write_stats(merged_stats, output_path)
    return merged_stats


def merge_root_tree_from_jobs(job_folders, output_path, root_filename, tree_name):
    merged_branch_data = {}
    for job_folder in job_folders:
        with uproot.open(Path(job_folder) / root_filename) as root_file:
            branch_data = root_tree_get_branch_data(root_file[tree_name], library="ak")
            for branch_name, values in branch_data.items():
                merged_branch_data.setdefault(branch_name, []).append(values)

    concatenated_branch_data = {
        branch_name: ak.concatenate(chunks) if len(chunks) > 1 else chunks[0]
        for branch_name, chunks in merged_branch_data.items()
    }
    branch_types = root_tree_get_branch_types(concatenated_branch_data)
    with uproot.recreate(output_path) as output_file:
        root_write_tree(output_file, tree_name, branch_types, concatenated_branch_data)
    return output_path


def summarize_child_global_times(job_folders, root_filename, tree_name):
    summaries = []
    for job_folder in job_folders:
        with uproot.open(Path(job_folder) / root_filename) as root_file:
            global_times = root_file[tree_name]["GlobalTime"].array(library="np")
        summaries.append(
            {
                "job_folder": Path(job_folder).name,
                "min": float(np.min(global_times)),
                "mean": float(np.mean(global_times)),
                "max": float(np.max(global_times)),
            }
        )
    return summaries


def check_child_global_time_ordering(
    child_summaries, time_unit, gap_tolerance_seconds=5.0
):
    is_ok = True
    previous_summary = None
    for summary in child_summaries:
        summary_min_seconds = summary["min"] / time_unit
        summary_mean_seconds = summary["mean"] / time_unit
        summary_max_seconds = summary["max"] / time_unit
        is_ok = utility.print_test(
            summary["min"] <= summary["mean"] <= summary["max"],
            f"{summary['job_folder']} GlobalTime ordering: "
            f"min={summary_min_seconds:.4f} s "
            f"mean={summary_mean_seconds:.4f} s "
            f"max={summary_max_seconds:.4f} s",
        ) and is_ok
        if previous_summary is not None:
            mean_is_monotonic = previous_summary["mean"] < summary["mean"]
            is_ok = utility.print_test(
                mean_is_monotonic,
                f"GlobalTime mean increases from {previous_summary['job_folder']} "
                f"({previous_summary['mean'] / time_unit:.4f} s) "
                f"to {summary['job_folder']} ({summary_mean_seconds:.4f} s)",
            ) and is_ok
            gap_seconds = (summary["min"] - previous_summary["max"]) / time_unit
            is_ok = utility.print_test(
                0.0 <= gap_seconds <= gap_tolerance_seconds,
                f"Boundary gap {previous_summary['job_folder']} -> {summary['job_folder']}: "
                f"{gap_seconds:.4f} s (tol={gap_tolerance_seconds})",
            ) and is_ok
        previous_summary = summary
    return is_ok


def compare_merged_root_with_reference(
    reference_root,
    merged_root,
    branch_name,
    plot_path,
):
    keys = [
        "KineticEnergy",
        "LocalTime",
        "GlobalTime",
        "TrackProperTime",
        "TimeFromBeginOfEvent",
    ]
    scalings = [1, 1, 1e-12, 1, 1]
    tolerances = [0.02, 0.02, 0.06, 0.02, 0.02]
    return utility.compare_root3(
        reference_root,
        merged_root,
        branch_name,
        branch_name,
        keys,
        keys,
        tolerances,
        scalings,
        scalings,
        plot_path,
    )


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test013_hl")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True
    sec = gate.g4_units.s

    reference_output = paths.output / "reference"
    reference_sim, _, reference_phsp_ion, reference_phsp_beta = (
        build_half_life_simulation(reference_output)
    )
    reference_sim.run(start_new_process=True)
    reference_stats = utility.read_stats_file(reference_output / "stats.txt")

    split_path = paths.output / "split_campaign_pool"
    split_sim, _, _, _ = build_half_life_simulation(
        split_path.parent / f"{split_path.name}_master_input"
    )
    split_root = gate.jobs_split(
        split_sim,
        5,
        split_path,
        policy="split_in_time_total",
    )
    summary = gate.jobs_run(
        split_root,
        backend="local_pool",
        backend_options={
            "n_workers": 4,
            "start_method": "spawn",
            "maxtasksperchild": 1,
        },
    )
    is_ok = utility.print_test(
        summary["submitted_jobs"] == 5,
        f"local_pool split summary:\n{pretty_json(summary)}",
    ) and is_ok

    status_data = wait_for_completed_jobs(split_root, expected_count=5)
    job_folders = [split_root / job["folder_name"] for job in status_data["jobs"]]

    ion_child_summaries = summarize_child_global_times(
        job_folders, "test013_decay_ion.root", "phsp_ion"
    )
    beta_child_summaries = summarize_child_global_times(
        job_folders, "test013_decay_beta_plus.root", "phsp_beta"
    )
    is_ok = check_child_global_time_ordering(ion_child_summaries, sec) and is_ok
    is_ok = check_child_global_time_ordering(beta_child_summaries, sec) and is_ok

    merged_stats_path = paths.output / "merged_stats.txt"
    merged_ion_root = paths.output / "merged_decay_ion.root"
    merged_beta_root = paths.output / "merged_decay_beta_plus.root"
    merged_stats = merge_stats_from_jobs(job_folders, merged_stats_path)
    merge_root_tree_from_jobs(
        job_folders, merged_ion_root, "test013_decay_ion.root", "phsp_ion"
    )
    merge_root_tree_from_jobs(
        job_folders, merged_beta_root, "test013_decay_beta_plus.root", "phsp_beta"
    )

    is_ok = utility.assert_stats_json(
        merged_stats.user_output.stats,
        reference_stats.user_output.stats,
        tolerance=0.1,
        track_types_flag=True,
    ) and is_ok
    is_ok = compare_merged_root_with_reference(
        reference_phsp_ion.get_output_path(),
        merged_ion_root,
        "phsp_ion",
        paths.output / "test013_decay_ion_split_compare.png",
    ) and is_ok
    is_ok = compare_merged_root_with_reference(
        reference_phsp_beta.get_output_path(),
        merged_beta_root,
        "phsp_beta",
        paths.output / "test013_decay_beta_split_compare.png",
    ) and is_ok

    utility.test_ok(is_ok)

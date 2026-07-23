#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

import awkward as ak
import numpy as np
import opengate as gate
import uproot
from opengate.actors.simulation_stats_helpers import sum_stats, write_stats
from opengate.contrib.root_helpers import (
    root_tree_get_branch_data,
    root_tree_get_branch_types,
    root_write_tree,
)
from opengate import g4_units
from opengate.tests import utility


def build_phsp_actor_simulation(
    output_dir,
    run_timing_intervals,
    source_n=None,
    source_activity=None,
    random_seed=321654,
):
    sim = gate.Simulation()

    sim.output_dir = Path(output_dir)
    sim.g4_verbose = False
    sim.visu = False
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.random_seed = random_seed

    m = gate.g4_units.m
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    plane = sim.add_volume("Tubs", "phase_space_plane")
    plane.mother = sim.world
    plane.material = "G4_AIR"
    plane.rmin = 0
    plane.rmax = 700 * mm
    plane.dz = 1 * nm
    plane.translation = [0, 0, -100 * mm]
    plane.color = [1, 0, 0, 1]

    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.type = "gauss"
    source.energy.mono = 1 * MeV
    source.energy.sigma_gauss = 0.5 * MeV
    source.position.type = "disc"
    source.position.radius = 20 * mm
    source.position.translation = [0, 0, 0 * mm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, -1]
    if (source_n is None) == (source_activity is None):
        raise ValueError("Provide exactly one of source_n or source_activity.")
    if source_n is not None:
        source.n = source_n
    if source_activity is not None:
        source.activity = source_activity * Bq if isinstance(source_activity, (int, float)) else source_activity

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"
    stats.track_types_flag = True

    phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phsp.attached_to = plane.name
    phsp.output_filename = "test019_phsp_actor.root"
    phsp.attributes = [
        "KineticEnergy",
        "PostPosition",
        "PrePosition",
        "PrePositionLocal",
        "ParticleName",
        "PreDirection",
        "PreDirectionLocal",
        "PostDirection",
        "TimeFromBeginOfEvent",
        "GlobalTime",
        "LocalTime",
        "EventPosition",
        "PDGCode",
    ]
    phsp.debug = False

    sim.run_timing_intervals = run_timing_intervals
    return sim, source, stats, phsp


def merge_stats_from_jobs(job_folders, output_path):
    merged_stats = None
    original_run_indices = set()
    for job_folder in job_folders:
        job_stats = utility.read_stats_file(Path(job_folder) / "stats.txt")
        merged_stats = (
            job_stats if merged_stats is None else sum_stats(merged_stats, job_stats)
        )
        with open(Path(job_folder) / "job_metadata.json", "r") as input_file:
            job_metadata = json.load(input_file)
        original_run_indices.update(job_metadata.get("original_run_indices", []))

    # A meaningful split-job merge must preserve the master simulation run
    # structure rather than summing child-local run counters.
    merged_stats.counts.runs = len(original_run_indices)
    write_stats(merged_stats, output_path)
    return merged_stats


def merge_phase_space_root_from_jobs(
    job_folders,
    output_path,
    root_filename="test019_phsp_actor.root",
    tree_name="PhaseSpace",
):
    merged_branch_data = {}
    for job_folder in job_folders:
        with uproot.open(Path(job_folder) / root_filename) as root_file:
            tree = root_file[tree_name]
            branch_data = root_tree_get_branch_data(tree, library="ak")
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


def _single_interval_midpoint(run_timing_intervals):
    if len(run_timing_intervals) != 1:
        raise ValueError(
            "This test helper expects exactly one run timing interval."
        )
    start, stop = run_timing_intervals[0]
    return 0.5 * (start + stop)


def check_child_phase_space_time_medians(job_folders, tolerance=0.05):
    is_ok = True
    for job_folder in job_folders:
        with open(Path(job_folder) / "job_metadata.json", "r") as input_file:
            job_metadata = json.load(input_file)
        expected_mid_time = _single_interval_midpoint(
            job_metadata["run_timing_intervals"]
        )
        with uproot.open(Path(job_folder) / "test019_phsp_actor.root") as root_file:
            global_time = root_file["PhaseSpace"]["GlobalTime"].array(library="np")
        median_time = float(np.median(global_time))
        is_ok = utility.print_test(
            abs(median_time - expected_mid_time) / expected_mid_time <= tolerance,
            f"{Path(job_folder).name} GlobalTime median: {median_time/g4_units.s:.4f} s ref={expected_mid_time/g4_units.s:.4f} s tol={tolerance}",
        ) and is_ok
    return is_ok


def check_merged_phase_space_time_median(
    merged_root, original_run_timing_intervals, tolerance=0.05
):
    expected_mid_time = _single_interval_midpoint(original_run_timing_intervals)
    with uproot.open(merged_root) as root_file:
        global_time = root_file["PhaseSpace"]["GlobalTime"].array(library="np")
    median_time = float(np.median(global_time))
    return utility.print_test(
        abs(median_time - expected_mid_time) / expected_mid_time <= tolerance,
        f"Merged GlobalTime median: {median_time/g4_units.s:.4f} s ref={expected_mid_time/g4_units.s:.4f} s tol={tolerance}",
    )


def compare_phase_space_roots(reference_root, merged_root, tree_name="PhaseSpace"):
    with uproot.open(reference_root) as reference_file:
        reference_tree = reference_file[tree_name]
        reference_arrays = reference_tree.arrays(library="np")
        reference_num_entries = reference_tree.num_entries
        reference_branch_names = sorted(reference_tree.keys())

    with uproot.open(merged_root) as merged_file:
        merged_tree = merged_file[tree_name]
        merged_arrays = merged_tree.arrays(library="np")
        merged_num_entries = merged_tree.num_entries
        merged_branch_names = sorted(merged_tree.keys())

    is_ok = True
    is_ok = utility.print_test(
        merged_branch_names == reference_branch_names,
        f"Phase-space branches match reference: {merged_branch_names}",
    ) and is_ok
    is_ok = utility.print_test(
        abs(merged_num_entries - reference_num_entries) / (merged_num_entries + reference_num_entries) * 2  <= 0.05,
        f"Phase-space entries: merged={merged_num_entries} ref={reference_num_entries}",
    ) and is_ok

    for branch_name, tolerance in (("KineticEnergy", 0.15),):
        merged_mean = merged_arrays[branch_name].mean()
        reference_mean = reference_arrays[branch_name].mean()
        is_ok = utility.print_test(
            abs(merged_mean - reference_mean) <= tolerance,
            f"{branch_name} mean: merged={merged_mean:.4f} ref={reference_mean:.4f} tol={tolerance}",
        ) and is_ok
        merged_std = merged_arrays[branch_name].std()
        reference_std = reference_arrays[branch_name].std()
        is_ok = utility.print_test(
            abs(merged_std - reference_std) <= tolerance,
            f"{branch_name} std: merged={merged_std:.4f} ref={reference_std:.4f} tol={tolerance}",
        ) and is_ok

    merged_radius = (
        merged_arrays["PrePosition_X"] ** 2 + merged_arrays["PrePosition_Y"] ** 2
    ) ** 0.5
    reference_radius = (
        reference_arrays["PrePosition_X"] ** 2 + reference_arrays["PrePosition_Y"] ** 2
    ) ** 0.5
    for label, merged_value, reference_value, tolerance in (
        (
            "PrePosition radius mean",
            merged_radius.mean(),
            reference_radius.mean(),
            1.0,
        ),
        # (
        #     "PrePosition radius std",
        #     merged_radius.std(),
        #     reference_radius.std(),
        #     1.0,
        # ),
    ):
        is_ok = utility.print_test(
            abs(merged_value - reference_value) <= tolerance,
            f"{label}: merged={merged_value:.4f} ref={reference_value:.4f} tol={tolerance}",
        ) and is_ok

    return is_ok

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import shutil
from pathlib import Path

import awkward as ak
import opengate as gate
import opengate.contrib.spect.siemens_intevo as intevo
import uproot
from opengate.contrib.root_helpers import (
    root_tree_get_branch_data,
    root_tree_get_branch_types,
    root_write_tree,
)
from opengate.sources.utility import get_spectrum
from opengate.tests import utility
from opengate.tests.src.geometry.test009_voxels_dynamic_helpers import (
    wait_for_completed_jobs,
)


def pretty_json(data):
    return json.dumps(data, indent=2, sort_keys=True)


def build_dynamic_multi_run_simulation(output_dir):
    sim = gate.Simulation()
    sim.visu = False
    sim.visu_type = "qt"
    sim.number_of_threads = 4
    sim.output_dir = Path(output_dir)
    sim.random_seed = 32175121

    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s
    mm = gate.g4_units.mm

    duration = 15 * sec
    number_of_angles = 7
    radius = 150 * mm

    spectrum = get_spectrum("Lu177", "gamma")
    source = sim.add_source("GenericSource", "src")
    source.attached_to = "world"
    source.particle = "gamma"
    source.activity = 10000 * Bq / sim.number_of_threads
    source.position.type = "point"
    source.direction.type = "iso"
    source.energy.type = "spectrum_discrete"
    source.energy.spectrum_energies = spectrum.energies
    source.energy.spectrum_weights = spectrum.weights

    phantom = sim.add_volume("Box", "phantom")
    phantom.material = "G4_AIR"
    phantom.size = [312, 240, 225]

    detector = sim.add_volume("Box", "detector")
    detector.material = "G4_AIR"
    detector.size = [2, 400, 400]
    detector.translation = [0, radius, 0]

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "stats.txt"
    stats.track_types_flag = True

    phsp_phantom = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp_phantom.attached_to = "phantom"
    phsp_phantom.attributes = [
        "KineticEnergy",
        "GlobalTime",
        "LocalTime",
        "PrePosition",
        "PostPosition",
        "ThreadID",
        "RunID",
        "EventID",
    ]
    phsp_phantom.output_filename = "a.root"
    phsp_phantom.steps_to_store = "exiting"

    phsp_detector = sim.add_actor("PhaseSpaceActor", "phsp2")
    phsp_detector.attached_to = "detector"
    phsp_detector.attributes = list(phsp_phantom.attributes)
    phsp_detector.output_filename = "b.root"
    phsp_detector.steps_to_store = "entering"

    step_time = duration / number_of_angles
    sim.run_timing_intervals = [
        [i * step_time, (i + 1) * step_time] for i in range(number_of_angles)
    ]

    step_angle = 360.0 / number_of_angles
    intevo.rotate_gantry(detector, radius, 0, step_angle, number_of_angles)

    sim.running_verbose_level = gate.logger.RUN
    return sim, phsp_detector, number_of_angles


def merge_phase_space_root_from_jobs_with_runid_remap(
    job_folders,
    output_path,
    root_filename="b.root",
    tree_name="phsp2",
):
    merged_branch_data = {}
    for job_folder in job_folders:
        with open(Path(job_folder) / "job_metadata.json", "r") as input_file:
            job_metadata = json.load(input_file)
        original_run_indices = job_metadata["original_run_indices"]
        if len(original_run_indices) != 1:
            raise RuntimeError(
                f"Expected exactly one original run index per job, got {original_run_indices} "
                f"for {job_folder}."
            )
        original_run_index = original_run_indices[0]

        with uproot.open(Path(job_folder) / root_filename) as root_file:
            tree = root_file[tree_name]
            branch_data = root_tree_get_branch_data(tree, library="ak")

        if "RunID" in branch_data:
            branch_data["RunID"] = ak.ones_like(branch_data["RunID"]) * int(
                original_run_index
            )

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


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test009_mr_mt")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True

    split_path = paths.output / "split_campaign"
    sim, _, number_of_angles = build_dynamic_multi_run_simulation(
        split_path.parent / f"{split_path.name}_master_input"
    )
    original_run_timing_intervals = list(sim.run_timing_intervals)

    split_root = gate.jobs_split(
        sim,
        number_of_angles,
        split_path,
        policy="split_time",
    )
    summary = gate.jobs_run(
        split_root,
        backend="local_pool",
        backend_options={
            "n_workers": number_of_angles,
            "start_method": "spawn",
            "maxtasksperchild": 1,
        },
    )
    is_ok = utility.print_test(
        summary["submitted_jobs"] == number_of_angles,
        f"local_pool split summary:\n{pretty_json(summary)}",
    ) and is_ok

    status_data = wait_for_completed_jobs(split_root, expected_count=number_of_angles)
    job_folders = []
    for job in status_data["jobs"]:
        job_folder = split_root / job["folder_name"]
        job_folders.append(job_folder)
        child_simulation = gate.create_sim_from_json(job_folder / "simulation.json")
        job_index = job["job_index"]
        expected_interval = [original_run_timing_intervals[job_index - 1]]
        is_ok = (
            utility.print_test(
                child_simulation.run_timing_intervals == expected_interval,
                f"{job['folder_name']} run timing interval: {child_simulation.run_timing_intervals}",
            )
            and is_ok
        )

    merged_root = paths.output / "merged_b.root"
    merge_phase_space_root_from_jobs_with_runid_remap(
        job_folders,
        merged_root,
        root_filename="b.root",
        tree_name="phsp2",
    )

    ref_root = paths.output_ref / "b.root"
    is_ok = (
        utility.compare_root3(
            ref_root,
            merged_root,
            "phsp2",
            "phsp2",
            keys1=["RunID"],
            keys2=["RunID"],
            tols=[0.070],
            scalings1=None,
            scalings2=None,
            img=paths.output / "output_split.png",
            nb_bins=50,
            hits_tol=8,
        )
        and is_ok
    )

    utility.test_ok(is_ok)

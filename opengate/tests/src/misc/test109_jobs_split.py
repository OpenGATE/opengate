#!/usr/bin/env python3

import json
import shutil
import numpy as np
import opengate as gate
from pathlib import Path
from opengate.tests import utility


def create_reference_image(output_path):
    # The split test only needs image filenames that survive JSON round-tripping.
    # A tiny MetaImage placeholder is enough because we never execute the simulation.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path = output_path.with_suffix(".raw")
    with open(raw_path, "wb") as raw_file:
        raw_file.write(np.zeros((5, 5, 5), dtype=np.float32).tobytes())
    with open(output_path, "w") as image_file:
        image_file.write("ObjectType = Image\n")
        image_file.write("NDims = 3\n")
        image_file.write("DimSize = 5 5 5\n")
        image_file.write("ElementType = MET_FLOAT\n")
        image_file.write("ElementSpacing = 1 1 1\n")
        image_file.write(f"ElementDataFile = {raw_path.name}\n")


def build_simulation(output_path, run_timing_intervals, source_n):
    sim = gate.Simulation()
    sim.output_dir = output_path

    source_image_1_path = output_path / "dynamic_source_1.mhd"
    source_image_2_path = output_path / "dynamic_source_2.mhd"
    create_reference_image(source_image_1_path)
    create_reference_image(source_image_2_path)

    box = sim.add_volume("Box", "dynamic_box")
    box.size = [10.0, 10.0, 10.0]
    box.add_dynamic_parametrisation(translation=[[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])

    source = sim.add_source("VoxelSource", "vox_source")
    source.particle = "gamma"
    source.n = source_n
    source.image = str(source_image_1_path)
    source.direction.type = "iso"
    source.energy.mono = 1.0 * gate.g4_units.MeV
    source.add_dynamic_parametrisation(image=[source_image_1_path, source_image_2_path])

    sim.run_timing_intervals = run_timing_intervals
    return sim, [source_image_1_path, source_image_2_path]


def get_dynamic_volume_translation(child_simulation):
    dynamic_box = child_simulation.volume_manager.get_volume("dynamic_box")
    return dynamic_box.dynamic_params["parametrisation_0"]["translation"]


def get_dynamic_source_images(child_simulation):
    dynamic_source = child_simulation.source_manager.get_source("vox_source")
    return [
        Path(path)
        for path in dynamic_source.dynamic_params["parametrisation_0"]["image"]
    ]


def get_source_n(child_simulation):
    dynamic_source = child_simulation.source_manager.get_source("vox_source")
    return list(dynamic_source.n)


def load_manifest(split_root):
    with open(split_root / "jobs_manifest.json", "r") as input_file:
        return json.load(input_file)


def load_child_simulation(job_folder):
    return gate.create_sim_from_json(job_folder / "simulation.json")


def load_job_metadata(job_folder):
    with open(job_folder / "job_metadata.json", "r") as input_file:
        return json.load(input_file)


def aggregate_counts_by_original_run(manifest, split_root):
    aggregated_counts = {}
    for job in manifest["jobs"]:
        job_folder = split_root / job["folder_name"]
        child_simulation = load_child_simulation(job_folder)
        job_metadata = load_job_metadata(job_folder)
        for original_run_index, count in zip(
            job_metadata["original_run_indices"], get_source_n(child_simulation)
        ):
            aggregated_counts.setdefault(original_run_index, 0)
            aggregated_counts[original_run_index] += int(count)
    return aggregated_counts


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test109")
    sec = gate.g4_units.s
    is_ok = True

    print(f"working folder = {paths.output}")
    print()
    # remove previous split_campaigns
    shutil.rmtree(paths.output / "split_campaigns", ignore_errors=True)

    # Validate the simple per-interval split policy first. Each original run is
    # divided independently, so each child should only refer to one original run.
    print("building a simulation (2 runs, 2 sources) ...")
    sim_1, source_images_1 = build_simulation(
        paths.output / "split_time_input",
        [(0.0 * sec, 2.0 * sec), (2.0 * sec, 6.0 * sec)],
        [100, 200],
    )
    split_root_1 = gate.jobs_split(
        sim_1, 4, paths.output / "split_campaigns", policy="split_time"
    )
    manifest_1 = load_manifest(split_root_1)
    print(f"split manifest    = {split_root_1}")

    utility.print_test(
        split_root_1.name.startswith("jobs_"),
        f"Split root folder name starts with jobs_: {split_root_1.name}",
    )
    is_ok = split_root_1.name.startswith("jobs_") and is_ok

    utility.print_test(
        [job["folder_name"] for job in manifest_1["jobs"]]
        == ["job0001", "job0002", "job0003", "job0004"],
        f"Job folders created: {[job['folder_name'] for job in manifest_1['jobs']]}",
    )
    is_ok = [job["folder_name"] for job in manifest_1["jobs"]] == [
        "job0001",
        "job0002",
        "job0003",
        "job0004",
    ] and is_ok

    first_job_folder = split_root_1 / "job0001"
    first_job_metadata = load_job_metadata(first_job_folder)
    first_child_simulation = load_child_simulation(first_job_folder)

    utility.print_test(
        first_job_metadata["parent_simulation_id"] == manifest_1["simulation_id"],
        "Job metadata references the correct parent simulation_id",
    )
    is_ok = (
        first_job_metadata["parent_simulation_id"] == manifest_1["simulation_id"]
        and is_ok
    )

    utility.print_test(
        first_child_simulation.run_timing_intervals == [[0.0 * sec, 1.0 * sec]],
        f"First split_time child run intervals: {first_child_simulation.run_timing_intervals}",
    )
    is_ok = (
        first_child_simulation.run_timing_intervals == [[0.0 * sec, 1.0 * sec]]
        and is_ok
    )

    utility.print_test(
        get_dynamic_volume_translation(first_child_simulation) == [[1.0, 0.0, 0.0]],
        f"First child dynamic volume translation subset: {get_dynamic_volume_translation(first_child_simulation)}",
    )
    is_ok = (
        get_dynamic_volume_translation(first_child_simulation) == [[1.0, 0.0, 0.0]]
        and is_ok
    )

    utility.print_test(
        get_dynamic_source_images(first_child_simulation) == [source_images_1[0]],
        "First child dynamic source image subset matches run 0 image",
    )
    is_ok = (
        get_dynamic_source_images(first_child_simulation) == [source_images_1[0]]
        and is_ok
    )

    utility.print_test(
        get_source_n(first_child_simulation) == [50],
        f"First child split_time source.n values: {get_source_n(first_child_simulation)}",
    )
    is_ok = get_source_n(first_child_simulation) == [50] and is_ok

    # Validate the total-time split policy next. The first child should span the
    # end of original run 0 and the beginning of original run 1.
    print()
    print()
    print("building another simulation (2 runs, 2 sources) ...")
    sim_2, source_images_2 = build_simulation(
        paths.output / "split_time_total_input",
        [(0.0 * sec, 1.0 * sec), (2.0 * sec, 5.0 * sec)],
        [10, 30],
    )
    split_root_2 = gate.jobs_split(
        sim_2, 3, paths.output / "split_campaigns", policy="split_time_total"
    )
    manifest_2 = load_manifest(split_root_2)
    print(f"split manifest  = {split_root_2}")

    job_1_total = load_child_simulation(split_root_2 / "job0001")
    job_2_total = load_child_simulation(split_root_2 / "job0002")
    job_3_total = load_child_simulation(split_root_2 / "job0003")
    job_1_total_metadata = load_job_metadata(split_root_2 / "job0001")

    # Active simulation time is 1 s + 3 s = 4 s, therefore each of the 3 jobs
    # should cover 4/3 s of active time.
    run_1_split_boundary_1 = (2.0 + 1.0 / 3.0) * sec
    run_1_split_boundary_2 = (2.0 + 5.0 / 3.0) * sec
    expected_job_1_intervals = [
        [0.0 * sec, 1.0 * sec],
        [2.0 * sec, run_1_split_boundary_1],
    ]
    expected_job_2_intervals = [[run_1_split_boundary_1, run_1_split_boundary_2]]
    expected_job_3_intervals = [[run_1_split_boundary_2, 5.0 * sec]]

    utility.print_test(
        np.allclose(job_1_total.run_timing_intervals, expected_job_1_intervals),
        f"split_time_total job0001 intervals: {job_1_total.run_timing_intervals}",
    )
    is_ok = (
        np.allclose(job_1_total.run_timing_intervals, expected_job_1_intervals)
        and is_ok
    )

    utility.print_test(
        np.allclose(job_2_total.run_timing_intervals, expected_job_2_intervals),
        f"split_time_total job0002 intervals: {job_2_total.run_timing_intervals}",
    )
    is_ok = (
        np.allclose(job_2_total.run_timing_intervals, expected_job_2_intervals)
        and is_ok
    )

    utility.print_test(
        np.allclose(job_3_total.run_timing_intervals, expected_job_3_intervals),
        f"split_time_total job0003 intervals: {job_3_total.run_timing_intervals}",
    )
    is_ok = (
        np.allclose(job_3_total.run_timing_intervals, expected_job_3_intervals)
        and is_ok
    )

    utility.print_test(
        job_1_total_metadata["original_run_indices"] == [0, 1],
        f"split_time_total first job original run indices: {job_1_total_metadata['original_run_indices']}",
    )
    is_ok = job_1_total_metadata["original_run_indices"] == [0, 1] and is_ok

    utility.print_test(
        get_dynamic_volume_translation(job_1_total)
        == [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
        "split_time_total first child keeps both dynamic translations",
    )
    is_ok = (
        get_dynamic_volume_translation(job_1_total)
        == [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]
        and is_ok
    )

    utility.print_test(
        get_dynamic_source_images(job_1_total) == source_images_2,
        "split_time_total first child keeps both dynamic source images",
    )
    is_ok = get_dynamic_source_images(job_1_total) == source_images_2 and is_ok

    # The split must not lose or create source events when child source.n arrays
    # are summed back over the original master runs.
    aggregated_counts = aggregate_counts_by_original_run(manifest_2, split_root_2)
    utility.print_test(
        aggregated_counts == {0: 10, 1: 30},
        f"split_time_total source.n counts aggregated by original run: {aggregated_counts}",
    )
    is_ok = aggregated_counts == {0: 10, 1: 30} and is_ok

    utility.test_ok(is_ok)

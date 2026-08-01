#!/usr/bin/env python3

"""Test split-job configuration materialization without executing Geant4.

This test focuses on three aspects of job splitting:

1. Split-policy structure:
   child run timing intervals, original-run mapping, dynamic-parameter
   subsetting, and ``source.number_of_primaries`` redistribution.
2. Input-file archiving:
   copied versus linked job-local inputs, including MetaImage ``.mhd/.raw``
   pairs and the current material-database workaround.
3. Rehydration contract:
   child ``simulation.json`` stores archived relative paths, while a rehydrated
   child simulation exposes absolute paths anchored inside its own job folder.
"""

import json
import os
import shutil
from pathlib import Path

import numpy as np
import opengate as gate

from opengate.jobs import DEFAULT_RESOLVED_SIMULATION_FILENAME
from opengate.serialization import load_json
from opengate.tests import utility


def create_reference_image(output_path):
    """Create a tiny MetaImage pair used only for JSON/path handling tests."""

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


def make_authored_path(
    absolute_path, simulation_root, input_path_mode, relative_reference_folder=None
):
    """Return the path representation authored into the simulation config."""

    absolute_path = Path(absolute_path).absolute()
    if input_path_mode == "absolute":
        return absolute_path
    if input_path_mode == "relative":
        if relative_reference_folder is None:
            relative_reference_folder = simulation_root
        try:
            return Path(os.path.relpath(absolute_path, relative_reference_folder))
        except ValueError:
            # Windows cannot express a relative path across drive letters.
            # For the material-database workaround in this test, author the
            # master simulation with an absolute path in that case and let the
            # split workflow archive/rewrite it for the child jobs as usual.
            return absolute_path
    raise ValueError(f"Unknown input_path_mode '{input_path_mode}'.")


def build_simulation(
    simulation_root,
    run_timing_intervals,
    source_n,
    material_db_source_path,
    input_path_mode="absolute",
):
    """Build a tiny split-ready simulation with several archived inputs."""

    simulation_root = Path(simulation_root).absolute()
    inputs_dir = simulation_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    sim = gate.Simulation()
    sim.simulation_dir = simulation_root
    sim.output_dir = Path("output")

    dynamic_source_1_absolute = inputs_dir / "dynamic_source_1.mhd"
    dynamic_source_2_absolute = inputs_dir / "dynamic_source_2.mhd"
    static_volume_absolute = inputs_dir / "static_volume_input.mhd"
    create_reference_image(dynamic_source_1_absolute)
    create_reference_image(dynamic_source_2_absolute)
    create_reference_image(static_volume_absolute)

    material_db_absolute = inputs_dir / "test109_materials.db"
    shutil.copy2(material_db_source_path, material_db_absolute)

    # Most input-file user infos should be expressed relative to the simulation
    # root when requested. MaterialDatabase.read_from_file(...) opens the file
    # immediately, so its relative form must be valid from the current process
    # working directory rather than only from sim.simulation_dir.
    dynamic_source_1_authored = make_authored_path(
        dynamic_source_1_absolute,
        simulation_root,
        input_path_mode,
    )
    dynamic_source_2_authored = make_authored_path(
        dynamic_source_2_absolute,
        simulation_root,
        input_path_mode,
    )
    static_volume_authored = make_authored_path(
        static_volume_absolute,
        simulation_root,
        input_path_mode,
    )
    material_db_authored = make_authored_path(
        material_db_absolute,
        simulation_root,
        input_path_mode,
        relative_reference_folder=Path.cwd(),
    )

    sim.volume_manager.add_material_database(material_db_authored)

    box = sim.add_volume("Box", "dynamic_box")
    box.size = [10.0, 10.0, 10.0]
    box.add_dynamic_parametrisation(translation=[[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])

    image_volume = sim.add_volume("Image", "static_image_volume")
    image_volume.image = static_volume_authored
    image_volume.voxel_materials = [[-np.inf, np.inf, "G4_AIR"]]

    source = sim.add_source("VoxelSource", "vox_source")
    source.particle = "gamma"
    source.number_of_primaries = source_n
    source.image = str(dynamic_source_1_authored)
    source.direction.type = "iso"
    source.energy.mono = 1.0 * gate.g4_units.MeV
    source.add_dynamic_parametrisation(
        image=[dynamic_source_1_authored, dynamic_source_2_authored]
    )

    sim.run_timing_intervals = run_timing_intervals

    return sim


def get_dynamic_volume_translation(child_simulation):
    dynamic_box = child_simulation.volume_manager.get_volume("dynamic_box")
    return dynamic_box.dynamic_params["parametrisation_0"]["translation"]


def get_dynamic_source_images(child_simulation):
    dynamic_source = child_simulation.source_manager.get_source("vox_source")
    return [
        Path(path)
        for path in dynamic_source.dynamic_params["parametrisation_0"]["image"]
    ]


def get_dynamic_source_image_names(child_simulation):
    return [path.name for path in get_dynamic_source_images(child_simulation)]


def get_source_n(child_simulation):
    dynamic_source = child_simulation.source_manager.get_source("vox_source")
    return list(dynamic_source.number_of_primaries)


def load_manifest(split_root):
    with open(split_root / "jobs_manifest.json", "r") as input_file:
        return json.load(input_file)


def load_child_simulation(job_folder):
    return gate.create_sim_from_json(job_folder / "simulation.json")


def load_child_simulation_dictionary(job_folder):
    with open(job_folder / "simulation.json", "r") as input_file:
        return load_json(input_file)


def load_job_metadata(job_folder):
    with open(job_folder / "job_metadata.json", "r") as input_file:
        return json.load(input_file)


def get_child_json_source_entry(job_folder):
    child_dict = load_child_simulation_dictionary(job_folder)
    return child_dict["source_manager"]["sources"]["vox_source"]["user_info"]


def get_child_json_static_volume_entry(job_folder):
    child_dict = load_child_simulation_dictionary(job_folder)
    return child_dict["volume_manager"]["volumes"]["static_image_volume"]["user_info"]


def get_child_json_material_database_filenames(job_folder):
    child_dict = load_child_simulation_dictionary(job_folder)
    return child_dict["volume_manager"]["material_database_filenames"]


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


def assert_archived_input_files(job_folder, link_files, expected_filenames):
    """Check that archived input files exist and use the requested mode."""

    is_ok = True
    for filename in expected_filenames:
        path = Path(job_folder) / filename
        exists = path.exists() or path.is_symlink()
        is_ok = (
            utility.print_test(
                exists,
                f"{Path(job_folder).name} contains archived input {filename}",
            )
            and is_ok
        )
        if exists:
            has_expected_mode = (
                path.is_symlink() if link_files else not path.is_symlink()
            )
            mode_label = "symlink" if link_files else "copied file"
            is_ok = (
                utility.print_test(
                    has_expected_mode,
                    f"{Path(job_folder).name} archived input mode for {filename}: {mode_label}",
                )
                and is_ok
            )
    return is_ok


def assert_child_json_archived_paths(job_folder, expected_dynamic_image_names):
    """Check the serialized child JSON stores archived relative filenames."""

    source_user_info = get_child_json_source_entry(job_folder)
    static_volume_user_info = get_child_json_static_volume_entry(job_folder)
    material_database_filenames = get_child_json_material_database_filenames(job_folder)

    source_image_ok = utility.print_test(
        source_user_info["image"] == Path("dynamic_source_1.mhd"),
        f"{Path(job_folder).name} child JSON source.image: {source_user_info['image']}",
    )
    dynamic_images_ok = utility.print_test(
        source_user_info["dynamic_params"]["parametrisation_0"]["image"]
        == [Path(name) for name in expected_dynamic_image_names],
        f"{Path(job_folder).name} child JSON dynamic source images: "
        f"{source_user_info['dynamic_params']['parametrisation_0']['image']}",
    )
    static_volume_ok = utility.print_test(
        static_volume_user_info["image"] == Path("static_volume_input.mhd"),
        f"{Path(job_folder).name} child JSON static volume image: {static_volume_user_info['image']}",
    )
    material_db_ok = utility.print_test(
        material_database_filenames == [Path("test109_materials.db")],
        f"{Path(job_folder).name} child JSON material DB filenames: {material_database_filenames}",
    )
    return source_image_ok and dynamic_images_ok and static_volume_ok and material_db_ok


def assert_rehydrated_child_paths(job_folder, expected_dynamic_image_names):
    """Check the rehydrated child simulation exposes archived absolute paths."""

    child_simulation = load_child_simulation(job_folder)
    source = child_simulation.source_manager.get_source("vox_source")
    image_volume = child_simulation.volume_manager.get_volume("static_image_volume")
    material_database_filenames = (
        child_simulation.volume_manager.material_database.filenames
    )

    expected_source_image = (Path(job_folder) / "dynamic_source_1.mhd").absolute()
    expected_dynamic_images = [
        (Path(job_folder) / name).absolute() for name in expected_dynamic_image_names
    ]
    expected_static_volume_image = (
        Path(job_folder) / "static_volume_input.mhd"
    ).absolute()
    expected_material_db = (Path(job_folder) / "test109_materials.db").absolute()

    source_ok = utility.print_test(
        Path(source.image) == expected_source_image,
        f"{Path(job_folder).name} rehydrated source.image: {source.image}",
    )
    dynamic_images_ok = utility.print_test(
        get_dynamic_source_images(child_simulation) == expected_dynamic_images,
        f"{Path(job_folder).name} rehydrated dynamic source images: {get_dynamic_source_images(child_simulation)}",
    )
    static_volume_ok = utility.print_test(
        Path(image_volume.image) == expected_static_volume_image,
        f"{Path(job_folder).name} rehydrated static volume image: {image_volume.image}",
    )
    material_db_ok = utility.print_test(
        len(material_database_filenames) == 1
        and Path(material_database_filenames[0]) == expected_material_db,
        f"{Path(job_folder).name} rehydrated material DB path: {material_database_filenames}",
    )
    return source_ok and dynamic_images_ok and static_volume_ok and material_db_ok


def run_input_path_rewrite_scenario(
    scenario_root,
    input_path_mode,
    link_files,
    run_timing_intervals,
    source_n,
    material_db_source_path,
):
    """Run one split-only scenario and inspect archived and rehydrated paths."""

    sim = build_simulation(
        scenario_root / "authored_simulation",
        run_timing_intervals,
        source_n,
        material_db_source_path,
        input_path_mode=input_path_mode,
    )
    split_root = gate.jobs_split(
        simulation=sim,
        number_of_jobs=2,
        campaign_dir=scenario_root / "campaign",
        policy="split_in_time_per_run",
        link_files=link_files,
        overwrite_existing_job_folders=True,
    ).campaign_dir
    manifest = load_manifest(split_root)
    expected_dynamic_image_names = {
        1: ["dynamic_source_1.mhd"],
        2: ["dynamic_source_2.mhd"],
    }
    archived_filenames_by_job = {
        # The static source.image always points to dynamic_source_1.mhd, while
        # the dynamic parametrisation contributes the per-run subset.
        1: [
            "dynamic_source_1.mhd",
            "dynamic_source_1.raw",
            "static_volume_input.mhd",
            "static_volume_input.raw",
            "test109_materials.db",
        ],
        2: [
            "dynamic_source_1.mhd",
            "dynamic_source_1.raw",
            "dynamic_source_2.mhd",
            "dynamic_source_2.raw",
            "static_volume_input.mhd",
            "static_volume_input.raw",
            "test109_materials.db",
        ],
    }

    is_ok = True
    for job in manifest["jobs"]:
        job_folder = split_root / job["folder_name"]
        job_index = job["job_index"]
        is_ok = (
            assert_archived_input_files(
                job_folder, link_files, archived_filenames_by_job[job_index]
            )
            and is_ok
        )
        is_ok = (
            assert_child_json_archived_paths(
                job_folder, expected_dynamic_image_names[job_index]
            )
            and is_ok
        )
        is_ok = (
            assert_rehydrated_child_paths(
                job_folder, expected_dynamic_image_names[job_index]
            )
            and is_ok
        )
    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test109")
    sec = gate.g4_units.s
    is_ok = True

    print(f"working folder = {paths.output}")
    print()

    # ---------------------------------------------------------------------
    # Section 1: split-policy structure and dynamic-parameter subsetting
    # ---------------------------------------------------------------------
    shutil.rmtree(paths.output / "auto_split_root", ignore_errors=True)
    shutil.rmtree(paths.output / "split_campaign_total", ignore_errors=True)

    print("building a simulation for split_in_time_per_run ...")
    sim_1 = build_simulation(
        paths.output / "split_in_time_per_run_input",
        [(0.0 * sec, 2.0 * sec), (2.0 * sec, 6.0 * sec)],
        [100, 200],
        paths.data / "GateMaterials.db",
        input_path_mode="absolute",
    )
    sim_1.random_seed = 123456
    split_root_1 = gate.jobs_split(
        simulation=sim_1,
        number_of_jobs=4,
        campaign_dir=paths.output / "auto_split_root",
        policy="split_in_time_per_run",
    ).campaign_dir
    manifest_1 = load_manifest(split_root_1)
    print(f"split manifest = {split_root_1}")

    utility.print_test(
        split_root_1.name == "auto_split_root",
        f"Split root folder name stays inside the test output directory: {split_root_1.name}",
    )
    is_ok = split_root_1.name == "auto_split_root" and is_ok

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
    fourth_child_simulation = load_child_simulation(split_root_1 / "job0004")

    utility.print_test(
        first_job_metadata["parent_simulation_id"] == manifest_1["simulation_id"],
        "Job metadata references the correct parent simulation_id",
    )
    is_ok = (
        first_job_metadata["parent_simulation_id"] == manifest_1["simulation_id"]
        and is_ok
    )

    utility.print_test(
        first_child_simulation.random_seed == 123457
        and fourth_child_simulation.random_seed == 123460,
        f"Integer master seed is offset by job index: "
        f"job0001={first_child_simulation.random_seed}, "
        f"job0004={fourth_child_simulation.random_seed}",
    )
    is_ok = (
        first_child_simulation.random_seed == 123457
        and fourth_child_simulation.random_seed == 123460
        and is_ok
    )

    utility.print_test(
        first_child_simulation.run_timing_intervals == [[0.0 * sec, 1.0 * sec]],
        f"First split_in_time_per_run child run intervals: {first_child_simulation.run_timing_intervals}",
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
        get_dynamic_source_image_names(first_child_simulation)
        == ["dynamic_source_1.mhd"],
        "First child dynamic source image subset matches run 0 image",
    )
    is_ok = (
        get_dynamic_source_image_names(first_child_simulation)
        == ["dynamic_source_1.mhd"]
        and is_ok
    )

    utility.print_test(
        get_source_n(first_child_simulation) == [50],
        f"First child split_in_time_per_run source.number_of_primaries values: {get_source_n(first_child_simulation)}",
    )
    is_ok = get_source_n(first_child_simulation) == [50] and is_ok

    print()
    print("building a simulation for split_in_time_total ...")
    sim_2 = build_simulation(
        paths.output / "split_in_time_total_input",
        [(0.0 * sec, 1.0 * sec), (2.0 * sec, 5.0 * sec)],
        [10, 30],
        paths.data / "GateMaterials.db",
        input_path_mode="absolute",
    )
    split_root_2 = gate.jobs_split(
        simulation=sim_2,
        number_of_jobs=3,
        campaign_dir=paths.output / "split_campaign_total",
        policy="split_in_time_total",
    ).campaign_dir
    manifest_2 = load_manifest(split_root_2)
    print(f"split manifest = {split_root_2}")

    with open(split_root_2 / DEFAULT_RESOLVED_SIMULATION_FILENAME, "r") as input_file:
        resolved_master_2 = load_json(input_file)
    job_1_total = load_child_simulation(split_root_2 / "job0001")
    job_2_total = load_child_simulation(split_root_2 / "job0002")
    job_3_total = load_child_simulation(split_root_2 / "job0003")
    job_1_total_metadata = load_job_metadata(split_root_2 / "job0001")

    resolved_master_seed_2 = resolved_master_2["user_info"]["current_random_seed"]
    utility.print_test(
        isinstance(resolved_master_seed_2, int)
        and resolved_master_2["user_info"]["random_seed"] == "auto"
        and job_1_total.random_seed == resolved_master_seed_2 + 1
        and job_2_total.random_seed == resolved_master_seed_2 + 2
        and job_3_total.random_seed == resolved_master_seed_2 + 3,
        f"Auto master seed is resolved once and offset by job index: "
        f"master={resolved_master_seed_2}, "
        f"jobs={[job_1_total.random_seed, job_2_total.random_seed, job_3_total.random_seed]}",
    )
    is_ok = (
        isinstance(resolved_master_seed_2, int)
        and resolved_master_2["user_info"]["random_seed"] == "auto"
        and job_1_total.random_seed == resolved_master_seed_2 + 1
        and job_2_total.random_seed == resolved_master_seed_2 + 2
        and job_3_total.random_seed == resolved_master_seed_2 + 3
        and is_ok
    )

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
        f"split_in_time_total job0001 intervals: {job_1_total.run_timing_intervals}",
    )
    is_ok = (
        np.allclose(job_1_total.run_timing_intervals, expected_job_1_intervals)
        and is_ok
    )

    utility.print_test(
        np.allclose(job_2_total.run_timing_intervals, expected_job_2_intervals),
        f"split_in_time_total job0002 intervals: {job_2_total.run_timing_intervals}",
    )
    is_ok = (
        np.allclose(job_2_total.run_timing_intervals, expected_job_2_intervals)
        and is_ok
    )

    utility.print_test(
        np.allclose(job_3_total.run_timing_intervals, expected_job_3_intervals),
        f"split_in_time_total job0003 intervals: {job_3_total.run_timing_intervals}",
    )
    is_ok = (
        np.allclose(job_3_total.run_timing_intervals, expected_job_3_intervals)
        and is_ok
    )

    utility.print_test(
        job_1_total_metadata["original_run_indices"] == [0, 1],
        f"split_in_time_total first job original run indices: {job_1_total_metadata['original_run_indices']}",
    )
    is_ok = job_1_total_metadata["original_run_indices"] == [0, 1] and is_ok

    utility.print_test(
        get_dynamic_volume_translation(job_1_total)
        == [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
        "split_in_time_total first child keeps both dynamic translations",
    )
    is_ok = (
        get_dynamic_volume_translation(job_1_total)
        == [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]
        and is_ok
    )

    utility.print_test(
        get_dynamic_source_image_names(job_1_total)
        == ["dynamic_source_1.mhd", "dynamic_source_2.mhd"],
        "split_in_time_total first child keeps both dynamic source images",
    )
    is_ok = (
        get_dynamic_source_image_names(job_1_total)
        == ["dynamic_source_1.mhd", "dynamic_source_2.mhd"]
        and is_ok
    )

    aggregated_counts = aggregate_counts_by_original_run(manifest_2, split_root_2)
    utility.print_test(
        aggregated_counts == {0: 10, 1: 30},
        f"split_in_time_total source.number_of_primaries counts aggregated by original run: {aggregated_counts}",
    )
    is_ok = aggregated_counts == {0: 10, 1: 30} and is_ok

    # ---------------------------------------------------------------------
    # Section 2: input archiving and rehydration path contract
    # ---------------------------------------------------------------------
    print()
    print("checking copied/linked and absolute/relative input path rewriting ...")

    rewrite_scenarios = [
        ("copied_absolute", "absolute", False),
        ("copied_relative", "relative", False),
        ("linked_absolute", "absolute", True),
        ("linked_relative", "relative", True),
    ]
    for scenario_name, input_path_mode, link_files in rewrite_scenarios:
        scenario_root = paths.output / f"path_rewrite_{scenario_name}"
        shutil.rmtree(scenario_root, ignore_errors=True)
        scenario_ok = run_input_path_rewrite_scenario(
            scenario_root,
            input_path_mode=input_path_mode,
            link_files=link_files,
            run_timing_intervals=[(0.0 * sec, 1.0 * sec), (1.0 * sec, 2.0 * sec)],
            source_n=[20, 40],
            material_db_source_path=paths.data / "GateMaterials.db",
        )
        is_ok = (
            utility.print_test(
                scenario_ok,
                f"Input path rewrite scenario {scenario_name}",
            )
            and is_ok
        )

    utility.test_ok(is_ok)

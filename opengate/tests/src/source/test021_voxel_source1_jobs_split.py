#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import shutil
from pathlib import Path

import itk
import opengate as gate
from scipy.spatial.transform import Rotation

from opengate.actors.simulation_stats_helpers import sum_stats, write_stats
from opengate.image import write_itk_image
from opengate.jobs import get_jobs_status
from opengate.tests import utility
from opengate.tests.src.geometry.test009_voxels_dynamic_helpers import (
    wait_for_completed_jobs,
)


def pretty_json(data):
    return json.dumps(data, indent=2, sort_keys=True)


def build_voxel_source_simulation(paths, output_dir, write_dose_to_disk):
    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 123456
    sim.output_dir = Path(output_dir)

    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s

    sim.world.size = [1.5 * m, 1 * m, 1 * m]

    fake = sim.add_volume("Box", "fake")
    fake.size = [36 * cm, 36 * cm, 36 * cm]
    fake.translation = [25 * cm, 0, 0]
    rotation = Rotation.from_euler("y", -25, degrees=True)
    rotation = rotation * Rotation.from_euler("x", -35, degrees=True)
    fake.rotation = rotation.as_matrix()

    ct = sim.add_volume("Image", "ct")
    ct.image = str(paths.data / "10x10x10.mhd")
    ct.mother = fake.name
    ct.voxel_materials = [[0, 10, "G4_WATER"]]
    ct.translation = [-3 * cm, 0, 0]
    ct.rotation = Rotation.from_euler("z", 45, degrees=True).as_matrix()

    source = sim.add_source("VoxelSource", "vox_source")
    source.attached_to = ct.name
    source.particle = "alpha"
    source.activity = 10000 * Bq
    source.image = str(paths.data / "five_pixels_10.mhd")
    source.direction.type = "iso"
    source.position.translation = gate.image.get_translation_between_images_center(
        ct.image, source.image
    )
    source.energy.mono = 1 * MeV

    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test021-1.mhd"
    dose.edep.write_to_disk = write_dose_to_disk
    dose.attached_to = ct.name
    image_info = gate.image.read_image_info(ct.image)
    dose.size = image_info.size
    dose.spacing = image_info.spacing
    dose.output_coordinate_system = "attached_to_image"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.all = 1 * mm

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"
    stats.track_types_flag = True

    sim.g4_commands_after_init.append("/tracking/verbose 0")
    sim.run_timing_intervals = [(0.0 * sec, 1.0 * sec)]

    return sim, dose, stats


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


def merge_images_from_jobs(job_folders, output_path):
    first_image = itk.imread(str(Path(job_folders[0]) / "test021-1_edep.mhd"))
    merged_array = itk.array_view_from_image(first_image).copy()

    for job_folder in job_folders[1:]:
        job_image = itk.imread(str(Path(job_folder) / "test021-1_edep.mhd"))
        merged_array += itk.array_view_from_image(job_image)

    merged_image = itk.image_from_array(merged_array)
    merged_image.SetSpacing(first_image.GetSpacing())
    merged_image.SetOrigin(first_image.GetOrigin())
    merged_image.SetDirection(first_image.GetDirection())
    write_itk_image(merged_image, output_path)
    return output_path


def check_dose_image(image):
    dose_sum = itk.array_view_from_image(image).sum()
    value_0 = image.GetPixel([5, 5, 5])
    value_1 = image.GetPixel([1, 5, 5])
    value_2 = image.GetPixel([1, 2, 5])
    value_3 = image.GetPixel([5, 2, 5])
    value_4 = image.GetPixel([6, 2, 5])
    tolerance = 0.15
    expected_sum = value_0 + value_1 + value_2 + value_3 + value_4

    def check_close(reference, value):
        relative_difference = abs(reference - value) / reference
        is_ok = relative_difference < tolerance
        utility.print_test(
            is_ok,
            f"Image diff {reference:.2f} vs {value:.2f} -> {relative_difference * 100.0:.2f}%",
        )
        return is_ok

    is_ok = check_close(dose_sum, expected_sum)
    is_ok = check_close(2000, value_0) and is_ok
    is_ok = check_close(2000, value_1) and is_ok
    is_ok = check_close(2000, value_2) and is_ok
    is_ok = check_close(2000, value_3) and is_ok
    is_ok = check_close(2000, value_4) and is_ok
    return is_ok


def assert_job_input_files(job_folder, link_files):
    expected_files = [
        "GateMaterials.db",
        "10x10x10.mhd",
        "10x10x10.raw",
        "five_pixels_10.mhd",
        "five_pixels_10.raw",
    ]

    is_ok = True
    for filename in expected_files:
        path = Path(job_folder) / filename
        exists = path.exists() or path.is_symlink()
        is_ok = utility.print_test(
            exists,
            f"{Path(job_folder).name} contains archived input {filename}",
        ) and is_ok
        if exists:
            has_expected_mode = path.is_symlink() if link_files else not path.is_symlink()
            mode_label = "symlink" if link_files else "copied file"
            is_ok = utility.print_test(
                has_expected_mode,
                f"{Path(job_folder).name} archived input mode for {filename}: {mode_label}",
            ) and is_ok
    return is_ok


def assert_rehydrated_child_inputs(job_folder):
    # Rebuild the child simulation from its JSON to verify that archived input
    # files are not only present in the folder, but also referenced correctly
    # after deserialization.
    child_simulation = gate.create_sim_from_json(Path(job_folder) / "simulation.json")
    ct = child_simulation.volume_manager.get_volume("ct")
    source = child_simulation.source_manager.get_source("vox_source")
    material_database_filenames = (
        child_simulation.volume_manager.material_database.filenames
    )

    expected_ct_image = (Path(job_folder) / "10x10x10.mhd").resolve()
    expected_source_image = (Path(job_folder) / "five_pixels_10.mhd").resolve()
    expected_material_db = (Path(job_folder) / "GateMaterials.db").resolve()

    is_ok = utility.print_test(
        Path(ct.image).resolve() == expected_ct_image,
        f"{Path(job_folder).name} rehydrated CT image path: {ct.image}",
    )
    is_ok = utility.print_test(
        Path(source.image).resolve() == expected_source_image,
        f"{Path(job_folder).name} rehydrated voxel-source image path: {source.image}",
    ) and is_ok
    is_ok = utility.print_test(
        len(material_database_filenames) == 1
        and Path(material_database_filenames[0]).resolve() == expected_material_db,
        f"{Path(job_folder).name} rehydrated material DB path: {material_database_filenames}",
    ) and is_ok
    return is_ok


def run_split_campaign(paths, split_path, backend, link_files, backend_options=None):
    sim, _, _ = build_voxel_source_simulation(
        paths,
        split_path.parent / f"{split_path.name}_master_input",
        write_dose_to_disk=True,
    )

    split_root = gate.jobs_split(
        sim,
        3,
        split_path,
        policy="split_in_time_total",
        link_files=link_files,
    )
    summary = gate.jobs_run(
        split_root,
        backend=backend,
        backend_options=backend_options,
    )
    mode_label = "linked" if link_files else "copied"
    is_ok = utility.print_test(
        summary["submitted_jobs"] == 3,
        f"{backend} {mode_label} submission summary:\n{pretty_json(summary)}",
    )

    initial_status = get_jobs_status(split_root)
    for job_status in initial_status["jobs"]:
        is_ok = utility.print_test(
            job_status["input_mode"] == mode_label,
            f"{backend} {job_status['folder_name']} input mode: {job_status['input_mode']}",
        ) and is_ok

    status_data = wait_for_completed_jobs(split_root, expected_count=3)
    job_folders = []
    for job in status_data["jobs"]:
        job_folder = split_root / job["folder_name"]
        job_folders.append(job_folder)
        is_ok = assert_job_input_files(job_folder, link_files) and is_ok
        is_ok = assert_rehydrated_child_inputs(job_folder) and is_ok

    merged_stats_path = (
        paths.output / f"{split_path.name}_{backend}_{mode_label}_merged_stats.txt"
    )
    merged_dose_path = (
        paths.output / f"{split_path.name}_{backend}_{mode_label}_merged_edep.mhd"
    )
    merged_stats = merge_stats_from_jobs(job_folders, merged_stats_path)
    merge_images_from_jobs(job_folders, merged_dose_path)

    merged_dose_image = itk.imread(str(merged_dose_path))
    is_ok = check_dose_image(merged_dose_image) and is_ok

    stats_ref = utility.read_stats_file(paths.output_ref / "stat021_ref_1.txt")
    stats_ref.counts.runs = 1
    is_ok = utility.assert_stats_json(
        merged_stats.user_output.stats,
        stats_ref.user_output.stats,
        tolerance=0.1,
        track_types_flag=True,
    ) and is_ok

    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test021")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True

    is_ok = (
        run_split_campaign(
            paths,
            paths.output / "split_campaign_sequential_copied",
            backend="local_sequential",
            link_files=False,
        )
        and is_ok
    )
    is_ok = (
        run_split_campaign(
            paths,
            paths.output / "split_campaign_pool_copied",
            backend="local_pool",
            link_files=False,
            backend_options={
                "n_workers": 2,
                "start_method": "spawn",
                "maxtasksperchild": 1,
            },
        )
        and is_ok
    )
    is_ok = (
        run_split_campaign(
            paths,
            paths.output / "split_campaign_sequential_linked",
            backend="local_sequential",
            link_files=True,
        )
        and is_ok
    )
    is_ok = (
        run_split_campaign(
            paths,
            paths.output / "split_campaign_pool_linked",
            backend="local_pool",
            link_files=True,
            backend_options={
                "n_workers": 2,
                "start_method": "spawn",
                "maxtasksperchild": 1,
            },
        )
        and is_ok
    )

    utility.test_ok(is_ok)

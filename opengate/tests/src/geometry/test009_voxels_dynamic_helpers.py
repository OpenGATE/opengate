#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from pathlib import Path

import itk
import opengate as gate
import numpy as np
from opengate.actors.simulation_stats_helpers import sum_stats, write_stats
from opengate.geometry.materials import read_voxel_materials
from opengate.image import write_itk_image
from opengate.jobs import get_jobs_status
from opengate.tests import utility
from scipy.spatial.transform import Rotation


def build_dynamic_voxel_simulation(
    paths,
    output_dir,
    run_timing_intervals,
    dynamic_image_paths=None,
    random_seed=123456,
):
    """Build the dynamic voxel test simulation with configurable timing/images."""

    output_dir = Path(output_dir)
    if dynamic_image_paths is None:
        dynamic_image_paths = [paths.data / "patient-4mm.mhd"] * len(
            run_timing_intervals
        )
    dynamic_image_paths = [Path(path) for path in dynamic_image_paths]

    if len(dynamic_image_paths) != len(run_timing_intervals):
        raise ValueError(
            "dynamic_image_paths must match the number of run_timing_intervals."
        )

    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.output_dir = output_dir
    sim.random_seed = random_seed

    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm

    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]
    fake.rotation = Rotation.from_euler("x", 20, degrees=True).as_matrix()

    patient = sim.add_volume("Image", "patient")
    patient.image = paths.data / "patient-4mm.mhd"
    patient.mother = "fake"
    patient.material = "G4_AIR"
    patient.voxel_materials = [
        [-2000, -900, "G4_AIR"],
        [-900, -100, "Lung"],
        [-100, 0, "G4_ADIPOSE_TISSUE_ICRP"],
        [0, 300, "G4_TISSUE_SOFT_ICRP"],
        [300, 800, "G4_B-100_BONE"],
        [800, 6000, "G4_BONE_COMPACT_ICRU"],
    ]
    patient.add_dynamic_parametrisation(image=dynamic_image_paths)

    voxel_materials_from_file = read_voxel_materials(
        paths.gate_data / "patient-HU2mat-v1.txt"
    )
    voxel_materials_from_file[0][0] = -2000
    assert patient.voxel_materials == voxel_materials_from_file
    patient.voxel_materials = voxel_materials_from_file
    patient.dump_label_image = output_dir / "test009_label.mhd"

    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 130 * MeV
    source.particle = "proton"
    source.position.type = "sphere"
    source.position.radius = 10 * mm
    source.position.translation = [0, 0, -14 * cm]
    source.activity = 10000 * Bq
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    patient.set_production_cut(
        particle_name="electron",
        value=3 * mm,
    )

    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test009-edep.mhd"
    dose.edep.keep_data_per_run = True
    dose.attached_to = "patient"
    dose.size = [99, 99, 99]
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.output_coordinate_system = "attached_to_image"
    dose.translation = [2 * mm, 3 * mm, -2 * mm]
    dose.hit_type = "random"

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"
    stats.track_types_flag = True

    sim.g4_commands_after_init.append("/tracking/verbose 0")
    sim.run_timing_intervals = run_timing_intervals

    return sim, patient, dose, stats


def get_dynamic_patient_images(simulation):
    patient = simulation.volume_manager.get_volume("patient")
    return [Path(path) for path in patient.dynamic_params["parametrisation_0"]["image"]]


def wait_for_completed_jobs(split_root, expected_count, timeout=180):
    """Wait until the requested number of split jobs report completed status."""

    deadline = time.time() + timeout
    last_statuses = []
    while time.time() < deadline:
        status_data = get_jobs_status(split_root)
        last_statuses = [
            job.get("execution_status") for job in status_data.get("jobs", [])
        ]
        if last_statuses.count("completed") == expected_count:
            return status_data
        time.sleep(0.5)
    raise RuntimeError(
        f"Timed out waiting for {expected_count} completed jobs. "
        f"Observed statuses: {last_statuses}"
    )


def merge_stats_from_jobs(job_folders, output_path):
    """Sum per-job statistics files and write the merged stats to disk."""

    merged_stats = None
    for job_folder in job_folders:
        job_stats = utility.read_stats_file(Path(job_folder) / "stats.txt")
        merged_stats = (
            job_stats if merged_stats is None else sum_stats(merged_stats, job_stats)
        )

    # Keep the merged stats comparable to the historical test009 reference,
    # which treats the whole simulation as one run even though several timing
    # intervals were used internally.
    merged_stats.counts.runs = 1
    write_stats(merged_stats, output_path)
    return merged_stats


def merge_images_from_jobs(job_folders, output_path):
    """Sum per-job dose images voxel-wise and write the merged image to disk."""


    # this is a manual merge for testing only. 
    # merging based on Actor/ActorOutput objects will be implemented soon 
    # and should be used in practice 
    first_image = itk.imread(str(Path(job_folders[0]) / "test009-edep_edep.mhd"))
    merged_array = np.array(itk.array_view_from_image(first_image), copy=True)

    for job_folder in job_folders[1:]:
        job_image = itk.imread(str(Path(job_folder) / "test009-edep_edep.mhd"))
        merged_array += itk.array_view_from_image(job_image)

    merged_image = itk.image_from_array(merged_array)
    merged_image.SetSpacing(first_image.GetSpacing())
    merged_image.SetOrigin(first_image.GetOrigin())
    merged_image.SetDirection(first_image.GetDirection())
    write_itk_image(merged_image, output_path)
    return output_path

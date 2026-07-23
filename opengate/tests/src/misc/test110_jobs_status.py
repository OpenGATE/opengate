#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from click.testing import CliRunner
import opengate as gate
from opengate.bin.opengate_jobs_status import (
    go as jobs_status_cli,
    print_jobs_status_summary,
)
from opengate.geometry.materials import read_voxel_materials
from opengate.jobs import get_jobs_status
from opengate.tests import utility
from scipy.spatial.transform import Rotation


def main():
    paths = utility.get_default_test_paths(
        __file__, "gate_test009_voxels", output_folder="test110"
    )

    # =========================================================================
    # Part 1: Basic split simulation & CLI status check
    # =========================================================================
    sim1 = gate.Simulation()
    sim1.output_dir = paths.output / "basic"

    box = sim1.add_volume("Box", "box")
    box.size = [10.0, 10.0, 10.0]

    source1 = sim1.add_source("GenericSource", "source")
    source1.particle = "gamma"
    source1.n = [100, 50]
    source1.direction.type = "iso"
    source1.energy.mono = 1.0 * gate.g4_units.MeV

    sim1.run_timing_intervals = [[0.0, 1.0], [1.0, 2.0]]

    split_root_folder1 = gate.jobs_split(
        sim1, number_of_jobs=2, split_path=paths.output / "basic", policy="split_time"
    )

    status1 = get_jobs_status(split_root_folder1)
    is_ok = status1["number_of_jobs"] == 2
    is_ok = is_ok and status1["summary_counts"]["ready"] == 2

    runner = CliRunner()
    result1 = runner.invoke(jobs_status_cli, [str(split_root_folder1), "-v"])
    is_ok = is_ok and (result1.exit_code == 0)
    is_ok = is_ok and ("Manifest file" in result1.output)
    is_ok = is_ok and ("job0001" in result1.output)
    is_ok = is_ok and ("job0002" in result1.output)

    manifest_file1 = split_root_folder1 / "jobs_manifest.json"
    result_manifest = runner.invoke(jobs_status_cli, [str(manifest_file1)])
    is_ok = is_ok and (result_manifest.exit_code == 0)
    is_ok = is_ok and ("Root directory" in result_manifest.output)

    print("\n--- Jobs Status Summary Output (Part 1: Basic) ---")
    print_jobs_status_summary(status1, verbose=True)

    is_ok = utility.print_test(is_ok, "Basic split status & CLI test")

    # =========================================================================
    # Part 2: Complex voxelized simulation & error detection
    # =========================================================================
    sim2 = gate.Simulation()
    sim2.output_dir = paths.output / "complex"
    sim2.g4_verbose = False
    sim2.g4_verbose_level = 1
    sim2.visu = False

    sim2.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm

    world = sim2.world
    world.size = [1 * m, 1 * m, 1 * m]

    fake = sim2.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]
    fake.rotation = Rotation.from_euler("x", 20, degrees=True).as_matrix()

    patient = sim2.add_volume("Image", "patient")
    patient.image = paths.data / "patient-4mm.mhd"
    patient.mother = "fake"
    patient.material = "G4_AIR"

    vm = read_voxel_materials(paths.gate_data / "patient-HU2mat-v1.txt")
    vm[0][0] = -2000
    patient.voxel_materials = vm

    source2 = sim2.add_source("GenericSource", "mysource")
    source2.energy.mono = 130 * MeV
    source2.particle = "proton"
    source2.position.type = "sphere"
    source2.position.radius = 10 * mm
    source2.position.translation = [0, 0, -14 * cm]
    source2.activity = 10000 * Bq
    source2.direction.type = "momentum"
    source2.direction.momentum = [0, 0, 1]

    patient.set_production_cut(
        particle_name="electron",
        value=3 * mm,
    )

    dose_actor = sim2.add_actor("DoseActor", "dose_actor")
    dose_actor.attached_to = "patient"
    dose_actor.edep_uncertainty.active = True
    dose_actor.size = [99, 99, 99]
    dose_actor.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose_actor.output_coordinate_system = "attached_to_image"
    dose_actor.translation = [2 * mm, 3 * mm, -2 * mm]

    stats_actor = sim2.add_actor("SimulationStatisticsActor", "Stats")
    stats_actor.track_types_flag = True

    split_root_folder2 = gate.jobs_split(
        sim2,
        3,
        paths.output / "complex" / "split_campaigns",
        policy="split_time",
        link_files=True,
    )

    status_initial2 = get_jobs_status(split_root_folder2)
    is_ok2 = status_initial2["summary_counts"]["ready"] == 3
    is_ok2 = (
        is_ok2 and (split_root_folder2 / "job0001" / "patient-4mm.mhd").is_symlink()
    )

    # Remove files in split folders to simulate errors
    (split_root_folder2 / "job0001" / "patient-4mm.raw").unlink(missing_ok=True)
    (split_root_folder2 / "job0002" / "job_metadata.json").unlink(missing_ok=True)

    status_err2 = get_jobs_status(split_root_folder2)
    is_ok2 = is_ok2 and status_err2["jobs"][0]["status"] == "missing_input_file"
    is_ok2 = is_ok2 and status_err2["jobs"][1]["status"] == "missing_metadata"
    is_ok2 = is_ok2 and status_err2["jobs"][2]["status"] == "ready"
    is_ok2 = is_ok2 and status_err2["summary_counts"]["ready"] == 1
    is_ok2 = is_ok2 and status_err2["summary_counts"]["missing_input_file"] == 1
    is_ok2 = is_ok2 and status_err2["summary_counts"]["missing_metadata"] == 1

    result2 = runner.invoke(jobs_status_cli, [str(split_root_folder2), "-v"])
    is_ok2 = is_ok2 and (result2.exit_code == 0)
    is_ok2 = is_ok2 and ("MISSING_INPUT_FILE" in result2.output)
    is_ok2 = is_ok2 and ("MISSING_METADATA" in result2.output)

    print("\n--- Jobs Status Summary Output (Part 2: Complex with Errors) ---")
    print_jobs_status_summary(status_err2, verbose=True)

    is_ok2 = utility.print_test(is_ok2, "Complex split error status & CLI test")

    utility.test_ok(is_ok and is_ok2)


if __name__ == "__main__":
    main()

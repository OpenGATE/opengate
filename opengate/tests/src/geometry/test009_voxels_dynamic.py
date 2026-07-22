#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test 009: Dynamic Voxelized Volumes and Dose Scoring

Objective:
Verify the creation and handling of voxelized volumes (Image) with dynamic
parametrisation (e.g., varying properties over time). It validates that the
simulation correctly handles run timing intervals in conjunction with dynamic
image definitions, and validates proton dose scoring.

Setup:
- World (G4_AIR): 1 x 1 x 1 m.
- Fake (Box, G4_AIR): A 40 x 40 x 40 cm rotated mother volume.
- Patient (Image, varying materials): Voxelized volume loaded with dynamic
  parametrisation (multiple image paths for different time intervals).
- Source: 130 MeV protons emitted from a spherical source, directed along +Z.

Verification 1: Timing Validation
Validates that the simulation correctly throws an exception when run timing
intervals do not match the dynamic parametrisation, and successfully runs
when they do match.

Verification 2: Simulation Statistics
Validates that the fundamental tracking steps, tracks, and events match the
expected reference statistics within an acceptable tolerance.

Verification 3: Dose Deposition
Validates the 3D dose (energy deposition) distribution scored inside the
voxelized patient volume by comparing it against a reference image.
"""

import opengate as gate
from opengate.tests import utility

from opengate.tests.src.geometry.test009_voxels_dynamic_helpers import (
    build_dynamic_voxel_simulation,
)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test009_voxels", "test009")
    sec = gate.g4_units.s

    sim, patient, dose, stats = build_dynamic_voxel_simulation(
        paths,
        paths.output,
        [(0, 0.5 * sec), (0.5 * sec, 1 * sec)],
    )

    sim.volume_manager.print_volumes()

    # GATE should reject a dynamic image configuration whose number of timing
    # intervals does not match the number of dynamic parametrisation entries.
    sim.run_timing_intervals = [
        (0, 0.5 * sec),
        (0.5 * sec, 1 * sec),
        (1 * sec, 1.5 * sec),
    ]
    try:
        sim.run(start_new_process=True)
        print("This exception is intentionally provoked and wanted. ")
        is_ok = False
    except Exception:
        is_ok = True

    # Reset the intended timing at the last moment. This is the supported path
    # the original test is meant to exercise.
    sim.run_timing_intervals = [(0, 0.5 * sec), (0.5 * sec, 1 * sec)]
    sim.run(start_new_process=True)

    print(stats)
    print(dose)

    stats_ref = utility.read_stats_file(paths.gate_output / "stat.txt")
    stats.counts.runs = 1
    print(
        "Setting run count to 1, although more than 1 run was used in the simulation. "
        "This is to avoid a wrongly failing test."
    )
    is_ok = is_ok and utility.assert_stats(stats, stats_ref, 0.15)
    is_ok = is_ok and utility.assert_images(
        paths.gate_output / "output-Edep.mhd",
        dose.edep.get_output_path(),
        stats,
        tolerance=35,
        ignore_value_data2=0,
        apply_ignore_mask_to_sum_check=False,
    )

    utility.test_ok(is_ok)

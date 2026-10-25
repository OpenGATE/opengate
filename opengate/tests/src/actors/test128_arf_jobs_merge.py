#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 127: jobs merge of an ARFActor with several runs.

As the DigitizerProjectionActor (test125), the ARF actor stacks all runs in the
same image: the slices of run r are the energy windows of run r, i.e. slices
[r * n_windows, (r + 1) * n_windows[. When the simulation is split into jobs,
each job only has a subset of the runs (local runs), and with the
"split_in_time_total" policy, a run can be split between two jobs. The merge
must add the slices of each local run of each job to the slices of the
corresponding original run.

The detector plane moves between runs (so each run gives a different image),
and the runs have different durations (so each run gives a different number of
counts).

What is checked:

1. The merged image has n_runs x n_windows slices (counts and squared_counts).
2. The split really has runs split between two jobs.
3. The merged image is exactly the sum of the slices of the jobs, placed
   according to the local to original run map of each job.
4. For each run, the number of counts and the mean position of the counts are
   close to a non-split reference simulation.
"""

import importlib.util
import json
import shutil
import sys

import numpy as np
import SimpleITK as sitk

import opengate as gate
from opengate.tests import utility


def create_simulation(paths, output_dir):
    sim = gate.Simulation()
    sim.output_dir = output_dir
    sim.random_seed = 123456
    sim.number_of_threads = 1

    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    keV = gate.g4_units.keV
    sec = gate.g4_units.s
    Bq = gate.g4_units.Bq

    world = sim.world
    world.size = [1 * gate.g4_units.m] * 3
    world.material = "G4_Galactic"

    # detector plane of the ARF (moves between runs)
    plane = sim.add_volume("Box", "plane")
    plane.size = [40 * cm, 40 * cm, 1 * nm]
    plane.material = "G4_Galactic"

    # runs of different durations, the plane is shifted along x for each run
    durations = [1, 2, 1, 3, 1]
    shifts = [-6, -3, 0, 3, 6]
    sim.run_timing_intervals = []
    start = 0
    for d in durations:
        sim.run_timing_intervals.append([start * sec, (start + d) * sec])
        start += d
    translations = [[s * cm, 0, 15 * cm] for s in shifts]
    plane.add_dynamic_parametrisation(translation=translations)
    plane.translation = translations[0]

    # source
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140.5 * keV
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.direction.type = "iso"
    source.activity = 50000 * Bq

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.global_production_cuts.all = 1 * gate.g4_units.km

    # ARF: all runs stacked in the same image
    arf = sim.add_actor("ARFActor", "arf")
    arf.attached_to = plane
    arf.output_filename = "arf.mhd"
    arf.batch_size = 1e5
    arf.image_size = [64, 64]
    arf.image_spacing = [4.41806 * mm, 4.41806 * mm]
    arf.distance_to_crystal = 74.625 * mm
    arf.pth_filename = paths.gate_data / "pth" / "arf_Tc99m_v3.pth"
    arf.enable_hit_slice = True
    arf.gpu_mode = utility.get_gpu_mode_for_tests()
    arf.squared_counts.active = True

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"

    return sim


def read_image(path):
    return sitk.GetArrayFromImage(sitk.ReadImage(str(path)))


def mean_x_per_run(array, n_windows):
    """Mean x (in pixels) of the counts of all windows of each run"""
    x = np.arange(array.shape[2])
    means = []
    for r in range(array.shape[0] // n_windows):
        a = array[r * n_windows : (r + 1) * n_windows].sum(axis=0)
        means.append((a.sum(axis=0) * x).sum() / a.sum())
    return np.array(means)


if __name__ == "__main__":
    # the ARF actor needs the garf package (and torch)
    if importlib.util.find_spec("garf") is None:
        print("The garf package is not installed (pip install garf): test skipped")
        utility.test_ok(True)
        sys.exit(0)

    paths = utility.get_default_test_paths(__file__, "gate_test043_garf", "test128")
    reference_output = paths.output / "reference"
    split_output = paths.output / "split"
    campaign_dir = paths.output / "campaign"
    for f in [reference_output, split_output, campaign_dir]:
        shutil.rmtree(f, ignore_errors=True)

    # reference: non-split simulation
    sim = create_simulation(paths, reference_output)
    n_runs = len(sim.run_timing_intervals)
    sim.run(start_new_process=True)

    # split simulation: the total time (8 sec) is split into 3 jobs, so some
    # runs are split between two jobs (merge from the campaign folder, as in
    # test125)
    sim = create_simulation(paths, split_output)
    controller = sim.run(
        number_of_jobs=3,
        wait_for_result=True,
        merge_after_run=False,
        campaign_dir=campaign_dir,
        split_policy="split_in_time_total",
    )
    merge_manager = gate.jobs_merge(campaign_dir)
    merge_manager.print_merge_summary()

    is_ok = True

    # local to original run map of each job
    run_maps = {}
    for f in sorted(campaign_dir.glob("job*/job_metadata.json")):
        run_maps[f.parent.name] = json.load(open(f))["original_run_indices"]
    contributors = {r: [] for r in range(n_runs)}
    for job, run_map in run_maps.items():
        for original_run in run_map:
            contributors[original_run].append(job)
    split_runs = [r for r, jobs in contributors.items() if len(jobs) > 1]
    is_ok = (
        utility.print_test(
            len(split_runs) > 0,
            f"Runs split between jobs: {split_runs} (map: {run_maps})",
        )
        and is_ok
    )

    # number of energy windows per run (from the reference image)
    reference = read_image(reference_output / "arf_counts.mhd")
    n_windows = reference.shape[0] // n_runs
    is_ok = (
        utility.print_test(
            reference.shape[0] == n_runs * n_windows and n_windows > 0,
            f"Reference: {reference.shape[0]} slices = {n_runs} runs x "
            f"{n_windows} energy windows",
        )
        and is_ok
    )

    for name in ["counts", "squared_counts"]:
        filename = f"arf_{name}.mhd"
        merged = read_image(split_output / filename)

        # 1. number of slices
        expected_shape = (n_runs * n_windows,) + reference.shape[1:]
        is_ok = (
            utility.print_test(
                merged.shape == expected_shape,
                f"{name}: merged shape {merged.shape} (expected {expected_shape})",
            )
            and is_ok
        )

        # 3. exact placement of the slices of the jobs
        expected = np.zeros(expected_shape)
        for job, run_map in run_maps.items():
            a = read_image(campaign_dir / job / "output" / filename)
            for local_run, original_run in enumerate(run_map):
                o, l = original_run * n_windows, local_run * n_windows
                expected[o : o + n_windows] += a[l : l + n_windows]
        is_ok = (
            utility.print_test(
                merged.shape == expected.shape
                and np.allclose(merged, expected, rtol=1e-5, atol=1e-6),
                f"{name}: merged slices are the job slices placed by original run",
            )
            and is_ok
        )

    # 4. comparison with the non-split reference, run by run
    merged = read_image(split_output / "arf_counts.mhd")
    for r in range(n_runs):
        m = merged[r * n_windows : (r + 1) * n_windows].sum()
        ref = reference[r * n_windows : (r + 1) * n_windows].sum()
        diff = abs(m - ref) / ref
        is_ok = (
            utility.print_test(
                diff < 0.1,
                f"Run {r}: counts merged {m:.1f} reference {ref:.1f} "
                f"(relative difference {diff * 100:.1f}%)",
            )
            and is_ok
        )
    mx = mean_x_per_run(merged, n_windows)
    rx = mean_x_per_run(reference, n_windows)
    is_ok = (
        utility.print_test(
            np.all(np.abs(mx - rx) < 1.0),
            f"Mean x of the counts per run (pixels): merged {np.round(mx, 2)} "
            f"reference {np.round(rx, 2)}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)

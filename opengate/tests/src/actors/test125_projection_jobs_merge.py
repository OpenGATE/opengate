#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 125: jobs merge of a DigitizerProjectionActor with several runs.

The projection actor stacks all runs in the same image: the slices of run r are
the channels of run r, i.e. slices [r * n_channels, (r + 1) * n_channels[.
When the simulation is split into jobs, each job only has a subset of the runs
(local runs), and with the "split_in_time_total" policy, a run can be split
between two jobs. The merge must add the slices of each local run of each job to
the slices of the corresponding original run.

The detector moves between runs (so each run gives a different image), and the
runs have different durations (so each run gives a different number of counts).

What is checked:

1. The merged image has n_runs x n_channels slices (counts and squared_counts).
2. The split really has runs split between two jobs.
3. The merged image is exactly the sum of the slices of the jobs, placed
   according to the local to original run map of each job.
4. For each run, the number of counts and the mean position of the counts are
   close to a non-split reference simulation.
"""

import json
import shutil

import numpy as np
import SimpleITK as sitk

import opengate as gate
from opengate.tests import utility


def create_simulation(output_dir):
    sim = gate.Simulation()
    sim.output_dir = output_dir
    sim.random_seed = 123456
    sim.number_of_threads = 1

    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    sec = gate.g4_units.s
    Bq = gate.g4_units.Bq

    world = sim.world
    world.size = [1 * gate.g4_units.m] * 3
    world.material = "G4_AIR"

    # detector (moves between runs)
    detector = sim.add_volume("Box", "detector")
    detector.size = [20 * cm, 20 * cm, 1 * cm]
    detector.material = "G4_SODIUM_IODIDE"

    # runs of different durations, the detector is shifted along x for each run
    durations = [1, 2, 1, 3, 1]
    shifts = [-6, -3, 0, 3, 6]
    sim.run_timing_intervals = []
    start = 0
    for d in durations:
        sim.run_timing_intervals.append([start * sec, (start + d) * sec])
        start += d
    translations = [[s * cm, 0, 10 * cm] for s in shifts]
    detector.add_dynamic_parametrisation(translation=translations)
    detector.translation = translations[0]

    # source
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140 * keV
    source.position.type = "point"
    source.direction.type = "iso"
    source.activity = 20000 * Bq

    # digitizer: hits, singles, energy window
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.attached_to = detector
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]
    hc.output_filename = None

    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.attached_to = detector
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.output_filename = None

    ew = sim.add_actor("DigitizerEnergyWindowsActor", "EnergyWindows")
    ew.attached_to = detector
    ew.input_digi_collection = "Singles"
    ew.channels = [{"name": "peak140", "min": 126 * keV, "max": 154 * keV}]
    ew.output_filename = None

    # projection: 2 channels, all runs stacked in the same image
    proj = sim.add_actor("DigitizerProjectionActor", "Projection")
    proj.attached_to = detector
    proj.input_digi_collections = ["Singles", "peak140"]
    proj.spacing = [5 * mm, 5 * mm]
    proj.size = [40, 40]
    proj.output_filename = "projection.mhd"
    proj.squared_counts.active = True

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"

    return sim, len(proj.input_digi_collections)


def read_image(path):
    return sitk.GetArrayFromImage(sitk.ReadImage(str(path)))


def mean_x_per_run(array, n_channels):
    """Mean x (in pixels) of the counts of the first channel of each run"""
    x = np.arange(array.shape[2])
    means = []
    for r in range(array.shape[0] // n_channels):
        a = array[r * n_channels]
        means.append((a.sum(axis=0) * x).sum() / a.sum())
    return np.array(means)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test125")
    reference_output = paths.output / "reference"
    split_output = paths.output / "split"
    campaign_dir = paths.output / "campaign"
    for f in [reference_output, split_output, campaign_dir]:
        shutil.rmtree(f, ignore_errors=True)

    # reference: non-split simulation
    sim, n_channels = create_simulation(reference_output)
    n_runs = len(sim.run_timing_intervals)
    sim.run(start_new_process=True)

    # split simulation: the total time (8 sec) is split into 3 jobs, so some
    # runs are split between two jobs.
    # The merge is done from the campaign folder (with merge_after_run=True,
    # the live simulation is rejected as target: the dynamic_geometry_actor
    # added during the split preparation is missing).
    sim, n_channels = create_simulation(split_output)
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

    for name in ["counts", "squared_counts"]:
        filename = f"projection_{name}.mhd"
        merged = read_image(split_output / filename)

        # 1. number of slices
        expected_shape = (n_runs * n_channels, 40, 40)
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
                o, l = original_run * n_channels, local_run * n_channels
                expected[o : o + n_channels] += a[l : l + n_channels]
        is_ok = (
            utility.print_test(
                merged.shape == expected.shape and np.allclose(merged, expected),
                f"{name}: merged slices are the job slices placed by original run",
            )
            and is_ok
        )

    # 4. comparison with the non-split reference, run by run
    merged = read_image(split_output / "projection_counts.mhd")
    reference = read_image(reference_output / "projection_counts.mhd")
    for r in range(n_runs):
        m = merged[r * n_channels : (r + 1) * n_channels].sum()
        ref = reference[r * n_channels : (r + 1) * n_channels].sum()
        diff = abs(m - ref) / ref
        is_ok = (
            utility.print_test(
                diff < 0.1,
                f"Run {r}: counts merged {m:.0f} reference {ref:.0f} "
                f"(relative difference {diff * 100:.1f}%)",
            )
            and is_ok
        )
    mx = mean_x_per_run(merged, n_channels)
    rx = mean_x_per_run(reference, n_channels)
    is_ok = (
        utility.print_test(
            np.all(np.abs(mx - rx) < 1.0),
            f"Mean x of the counts per run (pixels): merged {np.round(mx, 2)} "
            f"reference {np.round(rx, 2)}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)

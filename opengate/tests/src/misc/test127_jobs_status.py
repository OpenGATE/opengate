#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 127: jobs status of split campaigns, for several configurations.

The campaigns are only split (not run): the status is computed from the
campaign folder. For each configuration, the status must be consistent with
the split:

1. number of jobs, all jobs ready, no input check error
2. the jobs cover the whole campaign timeline: the first job starts at the
   beginning of the first run, the last job ends at the end of the last run,
   and each job starts where the previous one ends
3. the acquisition times of the jobs (sum of their run durations) add up to
   the total acquisition time of the campaign (gaps between runs excluded)
4. the number_of_primaries of the jobs add up to the ones of the simulation
5. the input files (given as Path or str) are listed and found in each job
6. the printed status (compact and verbose) contains the expected values

Configurations: one run (activity), several runs with gaps (activity),
several runs with number_of_primaries, both split policies
(split_in_time_total, split_in_time_per_run), input files copied or linked.
"""

import contextlib
import io
import json
import shutil
from pathlib import Path

import numpy as np

import opengate as gate
from opengate.bin.opengate_jobs import (
    format_campaign_timing,
    format_job_timing,
    print_jobs_status_summary,
)
from opengate.tests import utility

sec = gate.g4_units.s


def create_simulation(output_dir, run_timing_intervals, number_of_primaries=None):
    sim = gate.Simulation()
    sim.output_dir = output_dir
    sim.run_timing_intervals = run_timing_intervals
    data = paths.data

    # input files: the CT is given as a str, the source image as a Path
    ct = sim.add_volume("Image", "ct")
    ct.image = str(data / "ct_4mm.mhd")
    ct.material = "G4_AIR"
    ct.voxel_materials = [[-2000, 0, "G4_AIR"], [0, 5000, "G4_WATER"]]

    source = sim.add_source("VoxelSource", "source")
    source.attached_to = ct
    source.image = data / "source_three_areas_crop_3.5mm.mhd"
    source.particle = "gamma"
    source.energy.mono = 140 * gate.g4_units.keV
    if number_of_primaries is None:
        source.activity = 1000 * gate.g4_units.Bq
    else:
        source.number_of_primaries = number_of_primaries

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "stats.txt"
    return sim


def check_campaign(name, sim, number_of_jobs, policy, link_files=False):
    print(f"\n----- {name}: {number_of_jobs} jobs, {policy}, link_files={link_files}")
    campaign_dir = paths.output / name
    shutil.rmtree(campaign_dir, ignore_errors=True)
    intervals = [list(i) for i in sim.run_timing_intervals]
    source = sim.source_manager.sources["source"]
    primaries = None
    if source.activity <= 0:
        primaries = np.asarray(source.number_of_primaries).sum()
    gate.jobs_split(
        simulation=sim,
        campaign_dir=campaign_dir,
        number_of_jobs=number_of_jobs,
        policy=policy,
        link_files=link_files,
    )
    status = gate.jobs.jobs_status(campaign_dir)
    jobs = sorted(status["jobs"], key=lambda j: j["job_index"])
    is_ok = True

    # 1. jobs
    is_ok = (
        utility.print_test(
            status["number_of_jobs"] == number_of_jobs
            and len(jobs) == number_of_jobs
            and status["summary_counts"]["ready"] == number_of_jobs
            and all(j.get("input_check_error") is None for j in jobs),
            f"{number_of_jobs} jobs, all ready, no input check error",
        )
        and is_ok
    )

    # 2. timeline: the jobs cover the whole campaign, without gap nor overlap
    campaign_intervals = status["original_run_timing_intervals"]
    starts = [j["run_timing_intervals"][0][0] for j in jobs]
    ends = [j["run_timing_intervals"][-1][1] for j in jobs]
    contiguous = all(
        np.isclose(ends[i], starts[i + 1])
        or (  # per run policy: a job may end at a run end, the next one
            # starts at the next run start (gap between runs)
            any(np.isclose(ends[i], r[1]) for r in campaign_intervals)
            and any(np.isclose(starts[i + 1], r[0]) for r in campaign_intervals)
        )
        for i in range(len(jobs) - 1)
    )
    is_ok = (
        utility.print_test(
            np.isclose(starts[0], intervals[0][0])
            and np.isclose(ends[-1], intervals[-1][1])
            and contiguous,
            f"Jobs timeline from {starts[0] / sec:g} to {ends[-1] / sec:g} s "
            f"(campaign {intervals[0][0] / sec:g} to {intervals[-1][1] / sec:g} s)",
        )
        and is_ok
    )

    # 3. acquisition time
    acquisition = sum(b - a for a, b in intervals)
    jobs_acquisition = sum(b - a for j in jobs for a, b in j["run_timing_intervals"])
    is_ok = (
        utility.print_test(
            np.isclose(acquisition, jobs_acquisition),
            f"Acquisition time: campaign {acquisition / sec:g} s, "
            f"sum of the jobs {jobs_acquisition / sec:g} s",
        )
        and is_ok
    )

    # 4. number of primaries
    if primaries is not None:
        jobs_primaries = 0
        for j in jobs:
            d = json.load(open(campaign_dir / j["folder_name"] / "simulation.json"))
            n = d["source_manager"]["sources"]["source"]["user_info"][
                "number_of_primaries"
            ]
            jobs_primaries += np.asarray(n).sum()
        is_ok = (
            utility.print_test(
                jobs_primaries == primaries,
                f"Number of primaries: simulation {primaries}, sum of the jobs "
                f"{jobs_primaries}",
            )
            and is_ok
        )

    # 5. input files (CT given as str, source image as Path; mhd + raw)
    master_inputs = {Path(i["value"]).name for i in status["master_input_files"]}
    expected = {
        "ct_4mm.mhd",
        "ct_4mm.raw",
        "source_three_areas_crop_3.5mm.mhd",
        "source_three_areas_crop_3.5mm.raw",
    }
    n_inputs = {j["number_of_input_files"] for j in jobs}
    mode = {j["input_mode"] for j in jobs}
    is_ok = (
        utility.print_test(
            expected.issubset(master_inputs)
            and min(n_inputs) >= len(expected)
            and len(n_inputs) == 1
            and all(len(j["missing_input_files"]) == 0 for j in jobs)
            and mode == {"linked" if link_files else "copied"},
            f"Input files: master {sorted(master_inputs)}, "
            f"{n_inputs} files per job, {mode}",
        )
        and is_ok
    )

    # 6. printed status, compact and verbose
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print_jobs_status_summary(status, verbose=False)
    compact = out.getvalue()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print_jobs_status_summary(status, verbose=True)
    verbose = out.getvalue()
    n_lines = len(compact.splitlines())
    is_ok = (
        utility.print_test(
            f"{len(intervals)} run{'s' if len(intervals) > 1 else ''}, timeline"
            in compact
            and "total acquisition time" in compact
            and all(
                format_job_timing(j["run_timing_intervals"]) in compact for j in jobs
            )
            and format_campaign_timing(intervals) in compact
            and f"{len(intervals)} run(s)" in verbose
            and "Inputs:" in compact,
            f"Printed status ({n_lines} lines):\n{compact}",
        )
        and is_ok
    )
    return is_ok


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test127")
    is_ok = True

    # one run, activity
    sim = create_simulation(paths.output / "out", [[0, 10 * sec]])
    is_ok = check_campaign("one_run", sim, 3, "split_in_time_total") and is_ok

    # several runs with gaps between them (e.g. a SPECT acquisition), activity
    intervals = [[i * 1.1 * sec, (i * 1.1 + 1) * sec] for i in range(10)]
    sim = create_simulation(paths.output / "out", intervals)
    is_ok = check_campaign("runs_total", sim, 4, "split_in_time_total") and is_ok
    sim = create_simulation(paths.output / "out", intervals)
    is_ok = (
        check_campaign("runs_total_linked", sim, 4, "split_in_time_total", True)
        and is_ok
    )

    # several runs, number_of_primaries (one value per run)
    intervals = [[0, 1 * sec], [1 * sec, 3 * sec], [4 * sec, 5 * sec]]
    sim = create_simulation(paths.output / "out", intervals, [1000, 2000, 1001])
    is_ok = check_campaign("primaries_total", sim, 2, "split_in_time_total") and is_ok

    # split per run: the number of jobs is a multiple of the number of runs
    sim = create_simulation(paths.output / "out", intervals, [1000, 2000, 1001])
    is_ok = (
        check_campaign("primaries_per_run", sim, 6, "split_in_time_per_run") and is_ok
    )
    sim = create_simulation(paths.output / "out", intervals)
    is_ok = (
        check_campaign("activity_per_run", sim, 3, "split_in_time_per_run") and is_ok
    )

    utility.test_ok(is_ok)

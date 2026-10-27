#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 132: progress of the split jobs (local_pool backend).

1. each job writes job_progress.json in its folder: at the end, its status is
   'completed' and its number of generated events is the one of the job
2. the progress bar of the campaign shows all the jobs completed (100%)
"""

import io
import json
import shutil
from contextlib import redirect_stdout

import opengate as gate
from opengate.jobs import (
    JOB_PROGRESS_FILENAME,
    CampaignProgressBar,
    jobs_status,
)
from opengate.tests import utility

sec = gate.g4_units.s

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test132")
    campaign_dir = paths.output / "campaign"
    shutil.rmtree(paths.output, ignore_errors=True)

    sim = gate.Simulation()
    sim.output_dir = paths.output / "output"
    sim.progress_bar = True
    sim.run_timing_intervals = [[0, 1 * sec], [1 * sec, 2 * sec]]
    box = sim.add_volume("Box", "box")
    box.size = [20 * gate.g4_units.cm] * 3
    box.material = "G4_WATER"
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140 * gate.g4_units.keV
    source.activity = 2000 * gate.g4_units.Bq
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"

    controller = sim.run(
        number_of_jobs=2,
        wait_for_result=True,
        merge_after_run=False,
        campaign_dir=campaign_dir,
    )
    is_ok = utility.print_test(
        controller.stage == "completed", f"jobs: {controller.stage}"
    )

    # 1. the progress file of each job
    status_data = jobs_status(campaign_dir)
    for job in status_data["jobs"]:
        job_folder = campaign_dir / job["folder_name"]
        with open(job_folder / JOB_PROGRESS_FILENAME) as f:
            progress = json.load(f)
        with open(job_folder / "output" / "stats.txt") as f:
            events = json.load(f)["events"]["value"]
        b = (
            progress["status"] == "completed"
            and progress["generated_events"] == events
            and progress["expected_events"] > 0
        )
        utility.print_test(
            b,
            f"{job['folder_name']}: {progress['status']}, "
            f"{progress['generated_events']} generated events "
            f"(job: {events}), {progress['expected_events']} expected",
        )
        is_ok = is_ok and b

    # 2. the progress bar of the campaign
    bar = CampaignProgressBar(campaign_dir)
    output = io.StringIO()
    with redirect_stdout(output):
        bar.update(status_data)
        bar.close()
    line = output.getvalue().strip()
    print(line)
    b = line.startswith("Jobs 2/2") and "100.0%" in line
    is_ok = utility.print_test(b, "progress bar of the campaign: 100%") and is_ok

    utility.test_ok(is_ok)

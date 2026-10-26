#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 130: Control-C while the split jobs are running (local_pool backend).

The test runs itself as a child process (option --child), in a new session: the
child splits a simulation into 2 jobs and runs them with wait_for_result=True.
When the 2 jobs are running, SIGINT is sent to the process group of the child,
as Control-C in a terminal does. Then:

1. the child exits with the code 130, without any traceback, with a message
2. the 2 jobs are marked as 'interrupted' (not 'running' forever)
3. no process of the campaign is left
4. jobs_run() runs the interrupted jobs again, until they are completed
"""

import os
import signal
import subprocess
import sys
import time
import shutil

import opengate as gate
from opengate.tests import utility

sec = gate.g4_units.s


def run_child(campaign_dir):
    sim = gate.Simulation()
    sim.output_dir = campaign_dir.parent / "output"
    sim.run_timing_intervals = [[0, 1 * sec], [1 * sec, 2 * sec]]
    sim.world.material = "G4_AIR"
    box = sim.add_volume("Box", "box")
    box.size = [20 * gate.g4_units.cm] * 3
    box.material = "G4_WATER"
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 1 * gate.g4_units.MeV
    source.activity = 2e6 * gate.g4_units.Bq
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "stats.txt"
    sim.run(
        number_of_jobs=2,
        wait_for_result=True,
        merge_after_run=False,
        campaign_dir=campaign_dir,
    )


def job_statuses(campaign_dir):
    status = gate.jobs.jobs_status(campaign_dir)
    return [j.get("execution_status") for j in status["jobs"]], status


if __name__ == "__main__":
    if "--child" in sys.argv:
        run_child(gate.utility.Path(sys.argv[-1]))
        sys.exit(0)

    paths = utility.get_default_test_paths(__file__, None, "test130")
    if not hasattr(os, "killpg"):
        print("No process groups on this platform: test skipped")
        utility.test_ok(True)
        sys.exit(0)

    campaign_dir = paths.output / "campaign"
    shutil.rmtree(paths.output, ignore_errors=True)
    paths.output.mkdir(parents=True, exist_ok=True)
    log_file = paths.output / "child.log"
    is_ok = True

    # start the child in a new session (its own process group)
    with open(log_file, "w") as log:
        child = subprocess.Popen(
            [sys.executable, __file__, "--child", str(campaign_dir)],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pgid = os.getpgid(child.pid)

    # wait for the 2 jobs to be running (and the simulations started)
    t0 = time.time()
    running = False
    while time.time() - t0 < 120 and child.poll() is None:
        if (campaign_dir / gate.jobs.JOBS_MANIFEST_FILENAME).exists():
            st, _ = job_statuses(campaign_dir)
            if st.count("running") == 2:
                running = True
                break
        time.sleep(0.5)
    time.sleep(3)
    is_ok = utility.print_test(running, "The 2 jobs are running") and is_ok

    # Control-C
    os.killpg(pgid, signal.SIGINT)
    try:
        code = child.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(pgid, signal.SIGKILL)
        code = None
    time.sleep(1)
    log_text = log_file.read_text()
    print(log_text[-1500:])

    # 1. exit code, no traceback, message
    is_ok = (
        utility.print_test(
            code == 130
            and "Traceback" not in log_text
            and "Jobs interrupted by the user" in log_text,
            f"Child exit code {code} (130 expected), no traceback, message printed",
        )
        and is_ok
    )

    # 2. jobs marked as interrupted
    st, status = job_statuses(campaign_dir)
    is_ok = (
        utility.print_test(
            st == ["interrupted", "interrupted"]
            and status["execution_counts"]["interrupted"] == 2,
            f"Job statuses after Control-C: {st}",
        )
        and is_ok
    )

    # 3. no process left in the group of the child
    try:
        os.killpg(pgid, 0)
        left = True
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        left = False
    is_ok = utility.print_test(not left, "No process left after Control-C") and is_ok

    # 4. the interrupted jobs are run again
    gate.jobs_run(campaign_dir, detach=False)
    st, _ = job_statuses(campaign_dir)
    is_ok = (
        utility.print_test(
            st == ["completed", "completed"], f"Job statuses after jobs_run: {st}"
        )
        and is_ok
    )

    utility.test_ok(is_ok)

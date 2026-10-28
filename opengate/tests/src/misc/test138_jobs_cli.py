#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The opengate_jobs command line tool: split + run + merge in one command (local
backend by default), the subcommands split, run, status, merge and clean, the
JSON output, the failure of a job, and a relative output_dir inside the
campaign folder (kept when the simulation.json is written there).
"""

import json
import os
import shutil
import subprocess
import sys

import opengate as gate
from opengate.tests import utility

n = 20000


def opengate_jobs(*args, cwd=None):
    r = subprocess.run(
        [sys.executable, "-m", "opengate.bin.opengate_jobs"] + [str(a) for a in args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    print(f"opengate_jobs {' '.join(str(a) for a in args)} -> exit {r.returncode}")
    print(r.stdout[-2000:])
    print(r.stderr[-2000:])
    return r


def build_campaign(folder):
    sim = gate.Simulation()
    # relative to the current folder (simulation_dir is "."), which is the
    # parent of the campaign folder, so inside the campaign folder
    sim.output_dir = f"{folder.name}/output"
    cm = gate.g4_units.cm
    box = sim.add_volume("Box", "box")
    box.size = [10 * cm, 10 * cm, 10 * cm]
    box.material = "G4_WATER"
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 1 * gate.g4_units.MeV
    source.number_of_primaries = n
    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = box
    dose.size = [5, 5, 5]
    dose.spacing = [2 * cm, 2 * cm, 2 * cm]
    sim.add_actor("SimulationStatisticsActor", "stats")
    sim.to_json_file(directory=folder)


def number_of_events(output_folder):
    f = list(output_folder.glob("stats*.json"))
    if len(f) != 1:
        return None
    with open(f[0]) as fd:
        return json.load(fd)["events"]["value"]


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test138")
    shutil.rmtree(paths.output, ignore_errors=True)
    paths.output.mkdir(parents=True)
    campaign = paths.output / "campaign"
    campaign.mkdir()
    # as a script run in the folder that contains the campaign folder
    os.chdir(paths.output)
    build_campaign(campaign)
    is_ok = True

    # the relative output_dir is written relative to the campaign folder
    with open(campaign / "simulation.json") as f:
        output_dir = json.load(f)["user_info"]["output_dir"]
    b = output_dir == {"__pathlib_path__": ["output"]}
    is_ok = (
        utility.print_test(b, f"output_dir in simulation.json: {output_dir}") and is_ok
    )

    # split + run + merge in one command, local backend by default
    r = opengate_jobs("run", campaign, "-j", 3, "--json")
    result = json.loads(r.stdout) if r.returncode == 0 else {}
    merged = result.get("merge", {}).get("merged_output_dir")
    b = (
        r.returncode == 0
        and result.get("backend") == "local_pool"
        and result.get("submitted_jobs") == 3
        and merged == str((campaign / "output").resolve())
    )
    is_ok = utility.print_test(b, f"split + run + merge, merged in {merged}") and is_ok
    e = number_of_events(campaign / "output")
    is_ok = utility.print_test(e == n, f"merged events {e} (expected {n})") and is_ok
    b = all((campaign / f"job000{i}" / "job.log").exists() for i in (1, 2, 3))
    is_ok = utility.print_test(b, "one job.log per job folder") and is_ok

    # a different number of jobs needs --overwrite
    r = opengate_jobs("run", campaign, "-j", 2)
    b = r.returncode != 0 and "--overwrite" in r.stderr
    is_ok = utility.print_test(b, "already split: needs --overwrite") and is_ok

    # status
    r = opengate_jobs("status", campaign, "--json")
    counts = json.loads(r.stdout)["execution_counts"] if r.returncode == 0 else {}
    b = counts.get("completed") == 3
    is_ok = utility.print_test(b, f"status: {counts}") and is_ok

    # merge in another folder
    r = opengate_jobs("merge", campaign, "-o", paths.output / "merged2")
    e = number_of_events(paths.output / "merged2")
    b = r.returncode == 0 and e == n
    is_ok = utility.print_test(b, f"merge -o: {e} events") and is_ok

    # clean: only simulation.json and the merged output are kept
    r = opengate_jobs("clean", campaign)
    remaining = sorted(p.name for p in campaign.iterdir())
    b = r.returncode == 0 and remaining == ["output", "simulation.json"]
    is_ok = utility.print_test(b, f"clean: remaining {remaining}") and is_ok

    # split, then a job fails: the run reports it and the merge refuses
    r = opengate_jobs("split", campaign, "-j", 2)
    p = campaign / "job0002" / "simulation.json"
    with open(p) as f:
        d = json.load(f)
    d["source_manager"]["sources"]["source"]["user_info"]["particle"] = "no_particle"
    with open(p, "w") as f:
        json.dump(d, f)
    r = opengate_jobs("run", campaign, "--no-merge")
    b = r.returncode == 1 and "job0002: failed" in r.stderr and "job.log" in r.stderr
    is_ok = utility.print_test(b, "failed job reported") and is_ok
    r = opengate_jobs("merge", campaign)
    b = r.returncode != 0 and "Not all jobs completed" in r.stderr
    is_ok = utility.print_test(b, "merge refused") and is_ok

    # split again, run with one worker at a time, and merge
    r = opengate_jobs("run", campaign, "-j", 2, "--overwrite", "--workers", 1, "--json")
    result = json.loads(r.stdout) if r.returncode == 0 else {}
    b = (
        r.returncode == 0
        and result.get("jobs") == "2 completed"
        and number_of_events(campaign / "output") == n
    )
    is_ok = (
        utility.print_test(b, f"--overwrite --workers 1: {result.get('jobs')}")
        and is_ok
    )

    utility.test_ok(is_ok)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import click
import random
import sys
import json

from opengate.exception import fatal, colored, color_ok, color_error
from opengate_core.testsDataSetup import check_tests_data_folder
from opengate.bin.opengate_library_path import return_tests_path

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--test_id", "-i", default="all", help="Start test from this number")
@click.option(
    "--no_log_on_fail",
    default=False,
    is_flag=True,
    help="If set, do not print log on fail",
)
@click.option(
    "--random_tests",
    "-r",
    is_flag=True,
    default=False,
    help="Start the last 10 tests and 1/4 of the others randomly",
)
def go(test_id, random_tests, no_log_on_fail):
    mypath = return_tests_path()
    print("Looking for tests in: " + str(mypath))

    if not check_tests_data_folder():
        return False

    # Look if torch is installed
    torch = True
    torch_tests = [
        "test034_gan_phsp_linac.py",
        "test038_gan_phsp_spect_gan_my.py",
        "test038_gan_phsp_spect_gan_aa.py",
        "test038_gan_phsp_spect_gan_se.py",
        "test038_gan_phsp_spect_gan_ze.py",
        "test038_gan_phsp_spect_gan_mt.py",
        "test040_gan_phsp_pet_gan.py",
        "test043_garf.py",
        "test043_garf_mt.py",
        "test045_speedup_all_wip.py",
        "test047_gan_vox_source_cond.py",
    ]
    try:
        import torch
    except:
        torch = False

    ignored_tests = [
        "test045_speedup",  # this is a binary (still work in progress)
    ]

    onlyfiles = [f for f in os.listdir(str(mypath)) if (mypath / f).is_file()]

    files = []
    for f in onlyfiles:
        if "wip" in f or "WIP" in f:
            print(f"Ignoring: {f:<40} ")
            continue
        if "visu" in f:
            continue
        if "OLD" in f:
            continue
        if "old" in f:
            continue
        if "test" not in f:
            continue
        if ".py" not in f:
            continue
        if ".log" in f:
            continue
        if "all_tes" in f:
            continue
        if "_base" in f:
            continue
        if "_helpers" in f:
            continue
        if os.name == "nt" and "_mt" in f:
            continue
        if f in ignored_tests:
            continue
        if not torch and f in torch_tests:
            print(f"Ignoring: {f:<40} (Torch is not available) ")
            continue
        files.append(f)

    files = sorted(files)
    dashboard_dict = {}
    for file in files:
        dashboard_dict[file] = [""]
    if test_id != "all":
        test_id = int(test_id)
        files_new = []
        for f in files:
            id = int(f[4:7])
            if id >= test_id:
                files_new.append(f)
            else:
                print(f"Ignoring: {f:<40} (< {test_id}) ")
        files = files_new
    elif random_tests:
        files_new = files[-10:]
        prob = 0.25
        files = files_new + random.sample(files[:-10], int(prob * (len(files) - 10)))
        files = sorted(files)

    print(f"Running {len(files)} tests")
    print("-" * 70)

    failure = False

    for f in files:
        start = time.time()
        print(f"Running: {f:<46}  ", end="")
        cmd = "python " + str(mypath / f)
        log = str(mypath.parent / "log" / f) + ".log"
        r = os.system(f"{cmd} > {log} 2>&1")
        # subprocess.run(cmd, stdout=f, shell=True, check=True)
        if r == 0:
            print(colored.stylize(" OK", color_ok), end="")
            dashboard_dict[f] = [True]
        else:
            if r == 2:
                # this is probably a Ctrl+C, so we stop
                fatal("Stopped by user")
            else:
                print(colored.stylize(" FAILED !", color_error), end="")
                failure = True
                if not no_log_on_fail:
                    os.system("cat " + log)
                dashboard_dict[f] = [False]
        end = time.time()
        print(f"   {end - start:5.1f} s     {log:<65}")

    path_output_dashboard = mypath / ".." / "output_dashboard"
    os.makedirs(path_output_dashboard, exist_ok=True)
    dashboard_output = (
        "dashboard_output_"
        + sys.platform
        + "_"
        + str(sys.version_info[0])
        + "."
        + str(sys.version_info[1])
        + ".json"
    )
    with open(path_output_dashboard / dashboard_output, "w") as fp:
        json.dump(dashboard_dict, fp, indent=4)
    print(not failure)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()

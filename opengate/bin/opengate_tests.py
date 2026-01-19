#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from datetime import timedelta, datetime
import click
import random
import sys
import json
import re
from pathlib import Path
import subprocess
from multiprocessing import Pool
import yaml
from box import Box
import ast
import hashlib

from opengate.exception import fatal, colored, color_ok, color_error, color_warning
from opengate_core.testsDataSetup import check_tests_data_folder
from opengate.bin.opengate_library_path import return_tests_path
from opengate_core import GateInfo
from opengate.exception import warning

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--start_id", "-i", default="all", help="Start test from this number")
@click.option("--end_id", "-e", default="all", help="Start test up to this number")
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
@click.option(
    "--seed",
    "-s",
    default="",
    help="Seed for the random generator",
)
@click.option(
    "--processes_run",
    "-p",
    default="mp",
    help="Start simulations in single process mode: 'legacy', 'sp' or multi process mode 'mp'",
)
@click.option(
    "--num_processes",
    "-n",
    default="all",
    help="Start simulations in multiprocessing mode and run n processes - default is all available cores",
)
@click.option(
    "--run_previously_failed_jobs",
    "-f",
    default=False,
    is_flag=True,
    help="Run only the tests that failed in the previous evaluation.",
)
@click.option(
    "--g4_version",
    "-v",
    default="",
    help="Only for developers: overwrite the used geant4 version str to pass the check, style: v11.3.2",
)
def go(
    start_id,
    end_id,
    random_tests,
    seed,
    no_log_on_fail,
    processes_run,
    run_previously_failed_jobs,
    num_processes,
    g4_version,
):

    path_tests_src = return_tests_path()  # returns the path to the tests/src dir
    test_dir_path = path_tests_src.parent
    start = time.time()
    if not g4_version:
        try:
            g4_version = get_required_g4_version(path_tests_src)
        except:
            g4_version = "v11.3.2"
    if not check_g4_version(g4_version):
        warning(f'The geant4 version "{g4_version}" is not the expected version.')
        # return 0

    path_output_dashboard = test_dir_path / "output_dashboard"
    fpath_dashboard_output = path_output_dashboard / (
        "dashboard_output_"
        + sys.platform
        + "_"
        + str(sys.version_info[0])
        + "."
        + str(sys.version_info[1])
        + ".json"
    )

    if not run_previously_failed_jobs:
        files_to_run_avail, files_to_ignore = get_files_to_run()
        files_to_run = select_files(
            files_to_run_avail, start_id, end_id, random_tests, seed
        )
        download_data_at_first_run(files_to_run_avail[0])
        dashboard_dict_out = {k: [""] for k in files_to_run_avail}
    else:
        with open(fpath_dashboard_output, "r") as fp:
            dashboard_dict_out = json.load(fp)
            files_to_run = [k for k, v in dashboard_dict_out.items() if not v[0]]

    files_to_run_part1, files_to_run_part2_depending_on_part1 = (
        filter_files_with_dependencies(files_to_run, path_tests_src)
    )
    # print(f"{' ,'.join(files_to_run_part1)}")
    if len(files_to_run_part2_depending_on_part1) > 0:
        print(
            f"Found test cases with mutual dependencies, going to split evaluation into two sets. {len(files_to_run_part2_depending_on_part1)} tests will start right after first eval round."
        )
    runs_status_info = run_test_cases(
        files_to_run_part1, no_log_on_fail, processes_run, num_processes
    )

    if len(files_to_run_part2_depending_on_part1) > 0:
        print(
            "Now starting evaluation of tests depending on results of previous tests:"
        )
        runs_status_info_part2 = run_test_cases(
            files_to_run_part2_depending_on_part1,
            no_log_on_fail,
            processes_run,
            num_processes,
        )

        dashboard_dict, failure = status_summary_report(
            runs_status_info + runs_status_info_part2,
            files_to_run_part1 + files_to_run_part2_depending_on_part1,
            no_log_on_fail,
        )

    else:
        dashboard_dict, failure = status_summary_report(
            runs_status_info, files_to_run_part1, no_log_on_fail
        )
    end = time.time()
    run_time = timedelta(seconds=end - start)
    print(f"Evaluation took in total:   {run_time.seconds /60 :5.1f} min  ")
    dashboard_dict_out.update(dashboard_dict)
    if fpath_dashboard_output:
        os.makedirs(str(fpath_dashboard_output.parent), exist_ok=True)
        with open(fpath_dashboard_output, "w") as fp:
            json.dump(dashboard_dict_out, fp, indent=4)
    print(not failure)


def get_files_to_run():

    path_tests_src = return_tests_path()
    print("Looking for tests in: " + str(path_tests_src))

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
        "test081_simulation_optigan_with_random_seed.py",
        "test085_free_flight_mt.py",
        "test085_free_flight_ref_mt.py",
        "test085_free_flight_rotation.py",
    ]
    try:
        import torch
    except:
        torch = False

    ignored_tests = [
        "test045_speedup",  # this is a binary (still work in progress)
    ]
    path_tests_src = Path(path_tests_src)
    all_file_paths = []
    for file in path_tests_src.glob("**/test[0-9]*.py"):
        if file.is_file():
            all_file_paths.append(str(file.relative_to(path_tests_src)))

    # here we sort the paths
    all_file_paths = sorted(all_file_paths, key=lambda f: os.path.basename(f))

    ignore_files_containing = [
        "wip",
        "visu",
        "old",
        ".log",
        "all_tes",
        "_base",
        "_helpers",
    ]
    ignore_files_containing += ignored_tests
    print(
        f"Going to ignore all file names that contain any of: {', '.join(ignore_files_containing)}"
    )
    files_to_run = []
    files_to_ignore = []

    for filename in all_file_paths:
        eval_this_file = True
        reason_to_ignore = ""
        for string_to_ignore in ignore_files_containing:
            if string_to_ignore.lower() in filename.lower():
                eval_this_file = False
                reason_to_ignore = string_to_ignore
                continue
        if not torch and filename in torch_tests:
            reason_to_ignore = "Torch not avail"
            eval_this_file = False
        if os.name == "nt" and "_mt" in filename:
            eval_this_file = False
            reason_to_ignore = "mt & nt"
        if eval_this_file:
            files_to_run.append(filename)
        else:
            print(
                colored.stylize(
                    f"Ignoring: {filename:<40} --> {reason_to_ignore}",
                    color_warning,
                ),
                end="\n",
            )
            files_to_ignore.append(filename)
    print(
        f"Found {len(all_file_paths)} available test cases, of those {len(files_to_run)} files to run, and {len(files_to_ignore)} ignored."
    )
    return files_to_run, files_to_ignore


def get_required_g4_version(tests_dir: Path, rel_fpath=".github/workflows/main.yml"):
    fpath = tests_dir.parents[2] / rel_fpath
    with open(fpath) as f:
        githubworfklow = yaml.safe_load(f)
    g4 = githubworfklow["jobs"]["build_wheel"]["env"]["GEANT4_VERSION"]
    return g4


def check_g4_version(g4_version: str):
    v = GateInfo.get_G4Version().replace("$Name: ", "")
    v = v.replace("$", "")
    print(f"Detected Geant4 version: {v}")
    print(f"Required Geant4 version: {g4_version}")
    g4_should = decompose_g4_versioning(g4_version)
    g4_is = decompose_g4_versioning(v)
    if g4_should == g4_is:
        print(colored.stylize("Geant4 version is OK", color_ok), end="\n")
        return True
    else:
        print(f'{" ".join(map(str,g4_should))}')
        print(f'{" ".join(map(str,g4_is))}')
        print(colored.stylize("Geant4 version is not ok", color_error), end="\n")
        return False


def decompose_g4_versioning(g4str):
    # Check if patch is present:
    patchedVersion = False
    g4str = g4str.lower()
    if "-patch" in g4str:
        patchedVersion = True
        g4str = g4str.replace("-patch", "")
    # Regular expression pattern to match integers separated by . - _ or p
    pattern = r"\d+(?=[._\-p ])|\d+$"

    # Find all matches
    matches = re.findall(pattern, g4str)
    g4_version = [int(k) for k in matches]
    # removing 4 from "geant4"
    if g4_version and g4_version[0] == int(4):
        g4_version.pop(0)
    if not patchedVersion and len(g4_version) < 3:
        g4_version.append(0)
    return g4_version


def select_files(files_to_run, test_id, end_id, random_tests, seed):
    pattern = re.compile(r"^test([0-9]+)")

    if test_id != "all" or end_id != "all":
        test_id = int(test_id) if test_id != "all" else 0
        end_id = int(end_id) if end_id != "all" else sys.maxsize
        files_new = []
        for f in files_to_run:
            match = pattern.match(os.path.basename(f))
            f_test_id = int(float(match.group(1)))
            if f_test_id >= test_id and f_test_id <= end_id:
                files_new.append(f)
            else:
                if f_test_id < test_id:
                    print(f"Ignoring: {f:<40} (< {test_id}) ")
                else:
                    print(f"Ignoring: {f:<40} (> {end_id}) ")
        files_to_run = files_new
    elif random_tests:
        files_new = files_to_run[-10:]
        prob = 0.25
        if not seed == "":
            # Convert string to a hash and then to an integer
            hash_object = hashlib.md5(seed.encode())
            hash_hex = hash_object.hexdigest()
            seed_nb = int(hash_hex, 16) % (2**32)
            random.seed(seed_nb)

        files = files_new + random.sample(
            files_to_run[:-10], int(prob * (len(files_to_run) - 10))
        )
        files_to_run = sorted(files)
    return files_to_run


def get_main_function_args(file_dir, file_path):
    with open(file_dir / file_path, "r") as file:
        tree = ast.parse(file.read(), filename=file_path)

    # Find the 'main' function in the AST
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            # Extract the arguments of the main function

            args_info = {}
            # Handle cases where some arguments have no defaults
            num_defaults = len(node.args.defaults)
            num_args = len(node.args.args)
            non_default_args = num_args - num_defaults
            for i, arg in enumerate(node.args.args):
                arg_name = arg.arg
                if i >= non_default_args:
                    # Match argument with its default value
                    default_value = node.args.defaults[i - non_default_args]
                    # default_value_str = ast.dump(default_value).value()
                    if isinstance(default_value, ast.Constant):
                        default_value_str = default_value.value
                    else:
                        default_value_str = None
                else:
                    default_value_str = None
                args_info[arg_name] = default_value_str
            return args_info

    # Return None if no 'main' function is found
    return None


def analyze_scripts(file_dir, files):
    files_dependence_on = {}
    for file_path in files:
        args = get_main_function_args(file_dir, file_path)
        file_depending_on = None
        if args is not None and "dependency" in args:
            file_depending_on = args["dependency"]
        files_dependence_on[file_path] = file_depending_on
    return files_dependence_on


def filter_files_with_dependencies(files_to_run, path_tests_src):
    files_dependence_dict = analyze_scripts(path_tests_src, files_to_run)
    files_needed_for_other_tests = [
        os.path.join(os.path.dirname(file), needed_file)
        for file, needed_file in files_dependence_dict.items()
        if needed_file
    ]

    files_to_run_part1 = [f for f in files_to_run if not files_dependence_dict[f]]
    files_to_run_part1 += files_needed_for_other_tests
    files_to_run_part1 = list(set(files_to_run_part1))
    files_to_run_part2_depending_on_part1 = [
        f for f in files_to_run if files_dependence_dict[f]
    ]
    return files_to_run_part1, files_to_run_part2_depending_on_part1


def run_one_test_case(f, processes_run, path_tests_src):
    """
    This function is obsolete if we don't need os.system(run_cmd)
    """
    start = time.time()
    print(f"Running: {f:<46}  ", end="")
    cmd = "python " + str(path_tests_src / f)
    log = str(path_tests_src.parent / "log" / os.path.basename(f)) + ".log"
    if processes_run == "legacy":
        r = os.system(f"{cmd} > {log} 2>&1")
        shell_output = Box({"returncode": r, "log_fpath": log})
    else:
        shell_output = subprocess.run(
            f"{cmd} > {log} 2>&1",
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        r = shell_output.returncode
    if r == 0:
        print(colored.stylize(" OK", color_ok), end="")
    else:
        if r == 2:
            # this is probably a Ctrl+C, so we stop
            fatal("Stopped by user")
        else:
            print(colored.stylize(" FAILED !", color_error), end="")
    end = time.time()
    shell_output.run_time = start - end
    print(f"   {end - start:5.1f} s     {log:<65}")
    return shell_output


def download_data_at_first_run(f):
    print("Running one test case to trigger download of data if not available yet.")
    run_one_test_case_mp(f)


def run_one_test_case_mp(f):
    path_tests_src = return_tests_path()
    start = time.time()
    print(f"Running: {f:<46}  ", end="")
    cmd = "python " + str(path_tests_src / f)
    log = str(path_tests_src.parent / "log" / Path(os.path.basename(f)).stem) + ".log"

    # Write the command as the first line in the log file
    start = time.time()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log, "w") as log_file:
        log_file.write(f"\n\nDate/Time: {current_time}\n")
        log_file.write(f"Command: {cmd}\n\n")

    shell_output = subprocess.run(
        f"{cmd} >> {log} 2>&1", shell=True, check=False, capture_output=True, text=True
    )
    shell_output.log_fpath = log
    r = shell_output.returncode
    if r == 0:
        print(colored.stylize(" OK", color_ok), end="")
    else:
        if r == 2:
            # this is probably a Ctrl+C, so we stop
            fatal("Stopped by user")
        else:
            print(colored.stylize(" FAILED !", color_error), end="")
    end = time.time()
    shell_output.run_time = start - end
    print(f"\t {end - start:5.1f} s     {Path(log).name}")
    return shell_output


def run_test_cases(
    files: list, no_log_on_fail: bool, processes_run: str, num_processes: str
):
    path_tests_src = return_tests_path()
    # print("Looking for tests in: " + str(path_tests_src))
    print(f"Running {len(files)} tests")
    print("-" * 70)

    start = time.time()
    if processes_run in ["legacy"]:
        run_single_case = lambda k: run_one_test_case(k, processes_run, path_tests_src)
        runs_status_info = [run_single_case(file) for file in files]
    elif processes_run in ["sp"]:
        runs_status_info = [run_one_test_case_mp(file) for file in files]
    else:
        num_processes = int(float(num_processes)) if num_processes != "all" else None
        with Pool(processes=num_processes) as pool:
            runs_status_info = pool.map(run_one_test_case_mp, files)

    end = time.time()
    run_time = timedelta(seconds=end - start)
    print(f"Running tests took:   {run_time.seconds /60 :5.1f} min  ")
    return runs_status_info


def status_summary_report(runs_status_info, files, no_log_on_fail):

    dashboard_dict = {
        str(Path(k).name): [shell_output_k.returncode == 0]
        for k, shell_output_k in zip(files, runs_status_info)
    }

    tests_passed = [f for f in files if dashboard_dict[os.path.basename(f)][0]]
    tests_passed.sort()
    tests_failed = [f for f in files if not dashboard_dict[os.path.basename(f)][0]]
    tests_failed.sort()

    n_passed = sum([k[0] for k in dashboard_dict.values()])
    n_failed = sum([not k[0] for k in dashboard_dict.values()])

    # Display the logs of the failed jobs:
    for file, shell_output_k in zip(files, runs_status_info):
        if shell_output_k.returncode != 0 and not no_log_on_fail:
            print(
                str(Path(file).name),
                colored.stylize(": failed", color_error),
                end="\n",
            )
            if os.name == "nt":
                os.system("type " + shell_output_k.log_fpath)
            else:
                os.system("cat " + shell_output_k.log_fpath)

    print(f"Summary pass: {n_passed}/{len(files)} passed the tests:")
    for k in tests_passed:
        print(str(Path(k).name), colored.stylize(": passed", color_ok), end="\n")

    if n_failed > 0:
        print(f"Summary fail: {n_failed}/{len(files)} failed the tests:")
        for k in tests_failed:
            print(str(Path(k).name), colored.stylize(": failed", color_error), end="\n")

    fail_status = 0
    if n_passed == len(files) and n_failed == 0:
        print(colored.stylize("Yeahh, all tests passed!", color_ok))
        fail_status = 0
    else:
        print(colored.stylize("Oh no, not all tests passed.", color_error))
        fail_status = 1
    return dashboard_dict, fail_status


if __name__ == "__main__":
    go()

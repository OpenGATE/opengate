import ast
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from multiprocessing import Pool
from pathlib import Path

import yaml
from box import Box
from opengate_core import GateInfo
from opengate_core.testsDataSetup import check_tests_data_folder

from opengate.bin.opengate_library_path import return_tests_path
from opengate.exception import (
    color_error,
    color_ok,
    color_warning,
    colored,
    fatal,
    warning,
)

# --- Configuration Getters ---


def get_torch_dependent_tests():
    return [
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
    ]


def get_ignored_tests():
    return [
        "test045_speedup",  # this is a binary (still work in progress)
        "test094a_spect_simu_prim",  # to compute the reference data
        "test094b_spect_simu_scatter",  # to compute the reference data
        "test094c_build_sinogram",  # to compute the reference data
    ]


def get_ignored_patterns():
    return ["wip", "visu", "old", ".log", "all_tes", "_base", "_helpers"]


# --- Environment & G4 Version ---


def is_torch_available():
    try:
        import torch

        return True
    except ImportError:
        return False


def get_required_g4_version(tests_dir: Path, rel_fpath=".github/workflows/main.yml"):
    fpath = tests_dir.parents[2] / rel_fpath
    if not fpath.exists():
        return "v11.4.0"  # Safe fallback
    with open(fpath) as f:
        githubworfklow = yaml.safe_load(f)
    g4 = githubworfklow["jobs"]["build_wheel"]["env"]["GEANT4_VERSION"]
    return g4


def decompose_g4_versioning(g4str):
    patchedVersion = False
    g4str = g4str.lower()
    if "-patch" in g4str:
        patchedVersion = True
        g4str = g4str.replace("-patch", "")
    pattern = r"\d+(?=[._\-p ])|\d+$"
    matches = re.findall(pattern, g4str)
    g4_version = [int(k) for k in matches]
    if g4_version and g4_version[0] == int(4):
        g4_version.pop(0)
    if not patchedVersion and len(g4_version) < 3:
        g4_version.append(0)
    return g4_version


def check_g4_version(g4_version: str):
    v = GateInfo.get_G4Version().replace("$Name: ", "").replace("$", "")
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


def check_environment(g4_version_cli, path_tests_src):
    if not check_tests_data_folder():
        return False
    if not g4_version_cli:
        try:
            g4_version_cli = get_required_g4_version(path_tests_src)
        except Exception:
            g4_version_cli = "v11.4.0"
    if not check_g4_version(g4_version_cli):
        warning(f'The geant4 version "{g4_version_cli}" is not the expected version.')
    return True


def get_dashboard_file_path(test_dir_path):
    path_output_dashboard = test_dir_path / "output_dashboard"
    fpath_dashboard_output = path_output_dashboard / (
        f"dashboard_output_{sys.platform}_{sys.version_info[0]}.{sys.version_info[1]}.json"
    )
    return fpath_dashboard_output


# --- Discovery & Filtering Pipeline ---


def discover_all_tests(path_tests_src):
    all_file_paths = []
    for file in path_tests_src.glob("**/test[0-9]*.py"):
        if file.is_file():
            all_file_paths.append(str(file.relative_to(path_tests_src)))
    return sorted(all_file_paths, key=lambda f: os.path.basename(f))


def get_available_tests(all_file_paths):
    torch_avail = is_torch_available()
    torch_tests = get_torch_dependent_tests()
    ignore_files_containing = get_ignored_patterns() + get_ignored_tests()
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
                break

        if not torch_avail and filename in torch_tests:
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
                    f"Ignoring: {filename:<40} --> {reason_to_ignore}", color_warning
                )
            )
            files_to_ignore.append(filename)

    print(
        f"Found {len(all_file_paths)} available test cases, of those {len(files_to_run)} files to run, and {len(files_to_ignore)} ignored."
    )
    return files_to_run, files_to_ignore


def select_tests_by_id_or_random(files_to_run, start_id, end_id, random_tests, seed):
    pattern = re.compile(r"^test([0-9]+)")
    if start_id != "all" or end_id != "all":
        start_id_int = int(start_id) if start_id != "all" else 0
        end_id_int = int(end_id) if end_id != "all" else sys.maxsize
        files_new = []
        for f in files_to_run:
            match = pattern.match(os.path.basename(f))
            if match:
                f_test_id = int(float(match.group(1)))
                if start_id_int <= f_test_id <= end_id_int:
                    files_new.append(f)
                else:
                    if f_test_id < start_id_int:
                        print(f"Ignoring: {f:<40} (< {start_id_int}) ")
                    else:
                        print(f"Ignoring: {f:<40} (> {end_id_int}) ")
            else:
                files_new.append(f)
        files_to_run = files_new
    elif random_tests:
        files_new = files_to_run[-10:] if len(files_to_run) >= 10 else files_to_run
        prob = 0.25
        if seed:
            hash_hex = hashlib.md5(seed.encode()).hexdigest()
            random.seed(int(hash_hex, 16) % (2**32))
        pool = files_to_run[:-10] if len(files_to_run) > 10 else []
        files = files_new + random.sample(pool, int(prob * len(pool)))
        files_to_run = sorted(files)

    return files_to_run


# --- Dependency Graph Management ---


def get_main_function_args(file_dir, file_path):
    with open(file_dir / file_path, "r") as file:
        tree = ast.parse(file.read(), filename=file_path)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            args_info = {}
            num_defaults = len(node.args.defaults)
            num_args = len(node.args.args)
            non_default_args = num_args - num_defaults
            for i, arg in enumerate(node.args.args):
                if i >= non_default_args:
                    default_value = node.args.defaults[i - non_default_args]
                    default_value_str = (
                        default_value.value
                        if isinstance(default_value, ast.Constant)
                        else None
                    )
                else:
                    default_value_str = None
                args_info[arg.arg] = default_value_str
            return args_info
    return None


def analyze_scripts(file_dir, files):
    files_dependence_on = {}
    for file_path in files:
        args = get_main_function_args(file_dir, file_path)
        files_dependence_on[file_path] = (
            args.get("dependency") if args is not None else None
        )
    return files_dependence_on


def resolve_dependencies(files_to_run, path_tests_src):
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


# --- Test Execution ---


def run_one_test_case(f, processes_run, path_tests_src):
    start_time = time.time()
    print(f"Running: {f:<46}  ", end="")
    cmd = f"python {path_tests_src / f}"
    log = str(path_tests_src.parent / "log" / os.path.basename(f)) + ".log"

    os.makedirs(os.path.dirname(log), exist_ok=True)

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
        shell_output = Box({"returncode": shell_output.returncode, "log_fpath": log})

    if shell_output.returncode == 0:
        print(colored.stylize(" OK", color_ok), end="")
    elif shell_output.returncode == 2:
        fatal("Stopped by user")
    else:
        print(colored.stylize(" FAILED !", color_error), end="")

    end_time = time.time()
    shell_output.run_time = end_time - start_time
    print(f"   {shell_output.run_time:5.1f} s     {log:<65}")
    return shell_output


def run_one_test_case_mp(f):
    path_tests_src = return_tests_path()
    print(f"Running: {f:<46}  ", end="")
    cmd = f"python {path_tests_src / f}"
    log = str(path_tests_src.parent / "log" / Path(os.path.basename(f)).stem) + ".log"

    start_time = time.time()
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "w") as log_file:
        log_file.write(
            f"\n\nDate/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        log_file.write(f"Command: {cmd}\n\n")

    shell_output = subprocess.run(
        f"{cmd} >> {log} 2>&1", shell=True, check=False, capture_output=True, text=True
    )
    shell_output_box = Box({"returncode": shell_output.returncode, "log_fpath": log})

    if shell_output_box.returncode == 0:
        print(colored.stylize(" OK", color_ok), end="")
    elif shell_output_box.returncode == 2:
        fatal("Stopped by user")
    else:
        print(colored.stylize(" FAILED !", color_error), end="")

    end_time = time.time()
    shell_output_box.run_time = end_time - start_time
    print(f"\t {shell_output_box.run_time:5.1f} s     {Path(log).name}")
    return shell_output_box


def download_data_at_first_run(f):
    print("Running one test case to trigger download of data if not available yet.")
    run_one_test_case_mp(f)


def execute_test_batch(files, no_log_on_fail, processes_run, num_processes):
    path_tests_src = return_tests_path()
    print(f"Running {len(files)} tests\n{'-' * 70}")
    start_time = time.time()

    if processes_run in ["legacy"]:
        runs_status_info = [
            run_one_test_case(f, processes_run, path_tests_src) for f in files
        ]
    elif processes_run in ["sp"]:
        runs_status_info = [run_one_test_case_mp(f) for f in files]
    else:
        num_processes_int = (
            int(float(num_processes)) if num_processes != "all" else None
        )
        with Pool(processes=num_processes_int) as pool:
            runs_status_info = pool.map(run_one_test_case_mp, files)

    end_time = time.time()
    run_time = timedelta(seconds=end_time - start_time)
    print(f"Running tests took:   {run_time.seconds / 60 :5.1f} min  ")
    return runs_status_info


# --- Reporting ---


def generate_summary_report(runs_status_info, files, no_log_on_fail):
    dashboard_dict = {
        k: [shell_output_k.returncode == 0]
        for k, shell_output_k in zip(files, runs_status_info)
    }

    tests_passed = sorted([f for f in files if dashboard_dict[f][0]])
    tests_failed = sorted([f for f in files if not dashboard_dict[f][0]])

    n_passed = len(tests_passed)
    n_failed = len(tests_failed)

    for file, shell_output_k in zip(files, runs_status_info):
        if shell_output_k.returncode != 0 and not no_log_on_fail:
            print(file, colored.stylize(": failed", color_error), end="\n")
            if os.name == "nt":
                os.system("type " + shell_output_k.log_fpath)
            else:
                os.system("cat " + shell_output_k.log_fpath)

    print(f"Summary pass: {n_passed}/{len(files)} passed the tests:")
    for k in tests_passed:
        print(k, colored.stylize(": passed", color_ok), end="\n")

    if n_failed > 0:
        print(f"Summary fail: {n_failed}/{len(files)} failed the tests:")
        for k in tests_failed:
            print(k, colored.stylize(": failed", color_error), end="\n")

    if n_passed == len(files) and n_failed == 0:
        print(colored.stylize("Yeahh, all tests passed!", color_ok))
        fail_status = 0
    else:
        print(colored.stylize("Oh no, not all tests passed.", color_error))
        fail_status = 1

    return dashboard_dict, fail_status

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import click
import random
import sys
import json
import re
from pathlib import Path
import subprocess
from multiprocessing import Pool
#from functools import partial
from box import Box
import ast
import importlib.util
#import os

from opengate.exception import fatal, colored, color_ok, color_error, color_warning
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
@click.option(
    "--processes_run",
    "-p",
    default = "legacy",
    help="Start simulations in single process mode: 'legacy', 'sp' or multi process mode 'mp'" )

def go(test_id, random_tests, no_log_on_fail, processes_run):
    files_to_run, files_to_ignore = get_files_to_run(test_id, random_tests)
    files_to_run = select_files(files_to_run, test_id, random_tests)
    files_to_run, deselected_count, all_missing_modules = filter_files_by_missing_modules(files_to_run)
    run_test_cases(files_to_run, no_log_on_fail, processes_run)
    print(f'In total {deselected_count} tests were not started, because the following modules are missing: {", ".join(all_missing_modules)}')
    
def get_files_to_run(test_id, random_tests):

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

#    onlyfiles = [f for f in os.listdir(str(mypath)) if (mypath / f).is_file()]
    mypath = Path(mypath)
    all_file_paths = [file for file in mypath.glob('test[0-9]*.py') if file.is_file()]
    # here we sort the paths
    all_file_paths = sorted(all_file_paths) 
    
    ignore_files_containing = ['wip','visu','old', '.log', 'all_tes', '_base', '_helpers']
    ignore_files_containing += ignored_tests
    print(f"Going to ignore all file names that contain any of: {', '.join(ignore_files_containing)}")
    files_to_run = []
    files_to_ignore = []
    
    for f in all_file_paths:
        eval_this_file = True
        filename_for_pattern_search = str(f.name)
        reason_to_ignore = ''
        for string_to_ignore in ignore_files_containing:
            if string_to_ignore.lower() in filename_for_pattern_search.lower():
                eval_this_file = False
                reason_to_ignore = string_to_ignore
                continue
#        if not torch and filename_for_pattern_search in torch_tests:
##            print(f"Ignoring: {f:<40} (Torch is not available) ")
#            reason_to_ignore = 'Torch not avail'
#            eval_this_file = False
        if os.name == "nt" and "_mt" in f:
             eval_this_file = False
             reason_to_ignore = 'mt & nt'
        if eval_this_file:
            files_to_run.append(str(f))
        else:
            print(colored.stylize(f"Ignoring: {filename_for_pattern_search:<40} --> {reason_to_ignore}",color_warning), end = "\n")
            files_to_ignore.append(str(f))
    print(f"Found {len(all_file_paths)} available test cases, of those {len(files_to_run)} files to run, and {len(files_to_ignore)} ignored.")
    return files_to_run, files_to_ignore
    
def select_files(files_to_run, test_id, random_tests):
    pattern = re.compile(r"^test([0-9]+)")
    
    if test_id != "all":
        test_id = int(test_id)
        files_new = []
        for f in files_to_run:
            match = pattern.match(str(Path(f).name))
            f_test_id = int(float(match.group(1)))
            if f_test_id >= test_id:
                files_new.append(f)
            else:
                print(f"Ignoring: {f:<40} (< {test_id}) ")
        files_to_run = files_new
    elif random_tests:
        files_new = files_to_run[-10:]
        prob = 0.25
        files = files_new + random.sample(files_to_run[:-10], int(prob * (len(files_to_run) - 10)))
        files_to_run = sorted(files)
    return files_to_run

def get_imported_modules(filepath):
    """
    Parse the given Python file and return a list of imported module names.
    """
    imported_modules = set()
    with open(filepath, 'r', encoding='utf-8') as file:
        tree = ast.parse(file.read(), filename=filepath)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            imported_modules.add(node.module.split('.')[0])
    
    return imported_modules
def is_module_installed(module_name):
    """
    Check if a module is installed.
    """
    spec = importlib.util.find_spec(module_name)
    return spec is not None

def filter_files_by_missing_modules(filepaths):
    """
    Filter out files that have missing modules and return the valid files, 
    number of deselected files, and a set of all missing modules.
    """
    valid_files = []
    deselected_count = 0
    all_missing_modules = set()  # To track all missing modules

    for filepath in filepaths:
        missing_modules = []
        imported_modules = get_imported_modules(filepath)
        
        for module in imported_modules:
            if not is_module_installed(module):
                missing_modules.append(module)
                all_missing_modules.add(module)
        
        if not missing_modules:
            valid_files.append(filepath)
        else:
            deselected_count += 1
            print(f"Missing modules in {filepath}: {', '.join(missing_modules)}")
    
    return valid_files, deselected_count, all_missing_modules

def run_one_test_case(f, processes_run, mypath):
    start = time.time()
    print(f"Running: {f:<46}  ", end="")
    cmd = "python " + str(mypath / f)
    log = str(mypath.parent / "log" / f) + ".log"
    if processes_run  == 'legacy':
        r = os.system(f"{cmd} > {log} 2>&1")
        shell_output = Box({'returncode':r,'log_fpath':log})
        
    else:
        shell_output = subprocess.run(f"{cmd} > {log} 2>&1" , shell=True, check=False, capture_output=True, text = True)
        r = shell_output.returncode 
    if r == 0:
        print(colored.stylize(" OK", color_ok), end="")
        pass_fail_status = True
    else:
        if r == 2:
            # this is probably a Ctrl+C, so we stop
            fatal("Stopped by user")
        else:
            print(colored.stylize(" FAILED !", color_error), end="")
            
            pass_fail_status = False
    end = time.time()
    print(f"   {end - start:5.1f} s     {log:<65}")
    return shell_output


def run_one_test_case_mp(f):
    mypath = return_tests_path()
    start = time.time()
    print(f"Running: {f:<46}  ", end="")
    cmd = "python " + str(mypath / f)
    log = str(mypath.parent / "log" / f) + ".log"

    shell_output = subprocess.run(f"{cmd} > {log} 2>&1" , shell=True, check=False, capture_output=True, text = True)
    shell_output.log_fpath = log
    r = shell_output.returncode
    if r == 0:
        print(colored.stylize(" OK", color_ok), end="\n")
    else:
        if r == 2:
            # this is probably a Ctrl+C, so we stop
            fatal("Stopped by user")
        else:
            print(colored.stylize(" FAILED !", color_error), end="\n")
    end = time.time()
    print(f"   {end - start:5.1f} s     {log:<65}")
    return shell_output
def run_test_cases(files: list, no_log_on_fail: bool, processes_run:str):
    mypath = return_tests_path()
    print("Looking for tests in: " + str(mypath))
    print(f"Running {len(files)} tests")
    print("-" * 70)
    filenames = [str(Path(f).name) for f in files]

    failure = False
    start = time.time()
    if processes_run in ['legacy']:
        run_single_case = lambda k: run_one_test_case(k, processes_run, mypath)
        result_status_V =  list(map(run_single_case, files))
    elif  processes_run in ['sp']:
        result_status_V =  list(map(run_one_test_case_mp, files))
    else:
        with Pool() as pool:
            result_status_V =  pool.map(run_one_test_case_mp, files)
#        print('not implemented')
    dashboard_dict = {k: [shell_output_k.returncode == 0] for k, shell_output_k in zip(files, result_status_V)}
#    if not no_log_on_fail:
#        for k, shell_output_k in zip(files, result_status_V):
#            print(colored.stylize(f"{k} FAILED !", color_error), end="\n")
#            print(shell_output_k.stdout)
#            print('---------')
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
    tests_passed = [f for f in files if dashboard_dict[f][0]]
    tests_failed = [f for f in files if not dashboard_dict[f][0]]
   
    n_passed = sum([k[0] for k in dashboard_dict.values()] ) # [k_i++ for v in dashboard_dict.values() if v][0]
    n_failed = sum([not k[0] for k in dashboard_dict.values()] ) #[k_i++ for v in dashboard_dict.values() if not v]
    
    # Display the logs of the failed jobs:
    for file, shell_output_k in zip(files, result_status_V):
        if shell_output_k.returncode != 0 and not no_log_on_fail:
            print(str(Path(file).name), colored.stylize(f": failed", color_error), end ="\n")
            os.system("cat " + shell_output_k.log_fpath)
    
    print(f"Summary pass:{n_passed} of {len(files)} passed the tests:")
    for k in tests_passed:
        print(str(Path(k).name) , colored.stylize(f": passed", color_ok), end ="\n")
   
    print(f"Summary fail: {n_failed} of {len(files)} failed the tests:")
    for k in tests_failed:
        print(str(Path(k).name), colored.stylize(f": failed", color_error), end ="\n")
    
    end = time.time()
    print(f"Evaluation took in total:   {end - start:5.1f} s  ")
    if n_passed == len(files) and n_failed == 0:
        print(colored.stylize(f'Yeahh, all tests passed!', color_ok))
        return 0
    else:
        print(colored.stylize(f'Oh no, not all tests passed.',color_error))
        return 1
    

# --------------------------------------------------------------------------
#def main():
#    files, dashboard_dict = get_files_to_run()
#    go(files, dashboard_dict)

if __name__ == "__main__":
    go()
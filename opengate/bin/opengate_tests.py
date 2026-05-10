#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
from datetime import timedelta
import click

from opengate.bin.opengate_library_path import return_tests_path

try:
    import opengate_tests_helpers as helpers
except ImportError:
    from opengate.bin import opengate_tests_helpers as helpers

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
    help="Only for developers: overwrite the used geant4 version str to pass the check, style: v11.4.0",
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

    if not helpers.check_environment(g4_version, path_tests_src):
        return

    fpath_dashboard_output = helpers.get_dashboard_file_path(test_dir_path)

    if not run_previously_failed_jobs:
        all_files = helpers.discover_all_tests(path_tests_src)
        files_to_run_avail, files_to_ignore = helpers.get_available_tests(all_files)
        files_to_run = helpers.select_tests_by_id_or_random(
            files_to_run_avail, start_id, end_id, random_tests, seed
        )
        if files_to_run_avail:
            helpers.download_data_at_first_run(files_to_run_avail[0])
        dashboard_dict_out = {k: [""] for k in files_to_run_avail}
    else:
        with open(fpath_dashboard_output, "r") as fp:
            dashboard_dict_out = json.load(fp)
            files_to_run = [k for k, v in dashboard_dict_out.items() if not v[0]]

    files_to_run_part1, files_to_run_part2_depending_on_part1 = (
        helpers.resolve_dependencies(files_to_run, path_tests_src)
    )
    if len(files_to_run_part2_depending_on_part1) > 0:
        print(
            f"Found test cases with mutual dependencies, going to split evaluation into two sets. {len(files_to_run_part2_depending_on_part1)} tests will start right after first eval round."
        )
    runs_status_info = helpers.execute_test_batch(
        files_to_run_part1, no_log_on_fail, processes_run, num_processes
    )

    if len(files_to_run_part2_depending_on_part1) > 0:
        print(
            "Now starting evaluation of tests depending on results of previous tests:"
        )
        runs_status_info_part2 = helpers.execute_test_batch(
            files_to_run_part2_depending_on_part1,
            no_log_on_fail,
            processes_run,
            num_processes,
        )

        dashboard_dict, failure = helpers.generate_summary_report(
            runs_status_info + runs_status_info_part2,
            files_to_run_part1 + files_to_run_part2_depending_on_part1,
            no_log_on_fail,
        )

    else:
        dashboard_dict, failure = helpers.generate_summary_report(
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


if __name__ == "__main__":
    go()

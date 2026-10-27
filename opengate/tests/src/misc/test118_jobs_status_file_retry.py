#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
On Windows, a status file cannot be replaced while another process has it open,
and cannot be opened while it is being replaced: both raise PermissionError for a
few milliseconds. The job processes rewrite their status files while the
controller polls them, so these transient errors made split jobs fail at random
on Windows CI. Here we simulate them on any OS and check that the status files
are still written and read correctly.
"""

import builtins
import os
from unittest import mock

import opengate.jobs as jobs
from opengate.tests import utility


def fail_first_calls(function, n_failures, matches):
    """Wrap function so that its first n_failures calls matching the
    arguments raise PermissionError, like Windows does for a locked file."""
    state = {"failures": 0}

    def wrapper(*args, **kwargs):
        if matches(*args) and state["failures"] < n_failures:
            state["failures"] += 1
            raise PermissionError(13, "Permission denied (simulated)", str(args[0]))
        return function(*args, **kwargs)

    return wrapper, state


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test118")
    status_path = paths.output / jobs.JOB_EXECUTION_STATUS_FILENAME
    if status_path.exists():
        status_path.unlink()

    # do not wait long between attempts in this test
    jobs.STATUS_FILE_RETRY_DELAY_S = 0.001
    is_ok = True

    # 1) writing: os.replace fails a few times, then succeeds
    replace, state = fail_first_calls(os.replace, 3, lambda *a: True)
    with mock.patch("opengate.jobs.os.replace", replace):
        jobs._dump_json_atomic(status_path, {"status": "running"})
    b = state["failures"] == 3 and status_path.exists()
    utility.print_test(b, "Status file written after 3 PermissionErrors on replace")
    is_ok = is_ok and b

    leftovers = [p for p in paths.output.iterdir() if p.name.endswith(".tmp")]
    b = len(leftovers) == 0
    utility.print_test(b, "No temporary file left behind")
    is_ok = is_ok and b

    # 2) reading: open fails a few times, then succeeds
    real_open = builtins.open
    opener, state = fail_first_calls(
        real_open,
        3,
        lambda *a: str(a[0]).endswith(jobs.JOB_EXECUTION_STATUS_FILENAME),
    )
    with mock.patch("builtins.open", opener):
        data = jobs.load_job_execution_status(paths.output)
    b = state["failures"] == 3 and data == {"status": "running"}
    utility.print_test(b, f"Status file read after 3 PermissionErrors on open: {data}")
    is_ok = is_ok and b

    # 3) a lock that does not go away still raises after the retries
    replace, state = fail_first_calls(os.replace, 10**6, lambda *a: True)
    try:
        with mock.patch("opengate.jobs.os.replace", replace):
            jobs._dump_json_atomic(status_path, {"status": "completed"})
        b = False
    except PermissionError:
        b = state["failures"] == jobs.STATUS_FILE_RETRY_ATTEMPTS
    utility.print_test(
        b, f"A permanent lock still fails after {state['failures']} attempts"
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)

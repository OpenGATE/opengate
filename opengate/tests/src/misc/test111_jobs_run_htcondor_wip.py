#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
from pathlib import Path

import opengate as gate
from opengate.tests import utility

from opengate.tests.src.misc.test111_helpers_wip import (
    build_simple_simulation,
    load_backend_status,
)

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test112_htcondor")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True

    sim = build_simple_simulation(paths.output / "htcondor_input")
    split_root = gate.jobs_split(
        sim, 2, paths.output / "htcondor_campaign", policy="split_time"
    )

    # Realistic example for manual usage against a Condor installation:
    #
    # "submit_binary" and "submit_filename" are shown explicitly here for
    # clarity, but in normal usage they can be omitted because the defaults are
    # already "condor_submit" and "htcondor_jobs.submit".
    #
    # summary = gate.jobs_run(
    #     split_root,
    #     backend="htcondor",
    #     backend_options={
    #         "submit_binary": "condor_submit",
    #         "submit_filename": "htcondor_jobs.submit",
    #         "submit_file_commands": {
    #             "request_memory": "8 GB",
    #             "request_cpus": "4",
    #             "accounting_group": "group_gate.users",
    #             "requirements": '(OpSysAndVer =?= "Rocky8")',
    #             "+MyProject": '"radphys"',
    #         },
    #         "command_line_args": ["-batch-name", "gate_jobs"],
    #     },
    # )
    #
    # This test deliberately does not require a real Condor installation.
    # Instead of calling condor_submit, it uses a benign local command that
    # simply prints the submit filename it receives. This allows us to test the
    # submit-file rendering and command-line plumbing deterministically.
    summary = gate.jobs_run(
        split_root,
        backend="htcondor",
        backend_options={
            "submit_binary": "python3",
            "command_line_args": [
                "-c",
                "import pathlib, sys; print(pathlib.Path(sys.argv[1]).name)",
            ],
            "submit_filename": "gate_htcondor.submit",
            "submit_file_commands": {
                "request_memory": "8 GB",
                "request_cpus": "4",
            },
        },
    )

    submit_file_path = Path(summary["submit_file_path"])
    submit_file_content = submit_file_path.read_text()

    is_ok = is_ok and utility.print_test(
        summary["backend"] == "htcondor"
        and summary["submitted_jobs"] == 2
        and summary["skipped_completed_jobs"] == 0
        and summary["campaign_process_pid"] is None,
        f"htcondor submission summary: {summary}",
    )
    backend_status = load_backend_status(split_root)
    is_ok = is_ok and utility.print_test(
        backend_status is not None
        and backend_status["backend"] == "htcondor"
        and backend_status["status"] == "submitted"
        and backend_status["submitted_jobs"] == 2
        and backend_status["submit_file_path"] == str(submit_file_path)
        and backend_status["scheduler_job_id"] is None,
        f"htcondor backend status: {backend_status}",
    )

    is_ok = is_ok and utility.print_test(
        submit_file_path.name == "gate_htcondor.submit"
        and summary["submission_stdout"].strip() == "gate_htcondor.submit",
        f"htcondor submit command output: {summary['submission_stdout'].strip()}",
    )

    is_ok = is_ok and utility.print_test(
        "executable = opengate_job_runner" in submit_file_content
        and "arguments = . --backend htcondor" in submit_file_content
        and "initialdir = $(job_folder)" in submit_file_content,
        f"htcondor submit file core commands:\n{submit_file_content}",
    )

    is_ok = is_ok and utility.print_test(
        "request_memory = 8 GB" in submit_file_content
        and "request_cpus = 4" in submit_file_content,
        f"htcondor custom submit commands:\n{submit_file_content}",
    )

    is_ok = is_ok and utility.print_test(
        str((split_root / "job0001").resolve()) in submit_file_content
        and str((split_root / "job0002").resolve()) in submit_file_content
        and "queue job_folder from (" in submit_file_content,
        "htcondor queue statement contains both job folders",
    )

    utility.test_ok(is_ok)

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


def render_test_slurm_submit_script(job_folders_file_path, **kwargs):
    job_runner_command = kwargs["job_runner_command"]
    lines = [
        "#!/bin/sh",
        f'#SBATCH --partition={kwargs["partition"]}',
        f'#SBATCH --cpus-per-task={kwargs["cpus_per_task"]}',
        f'#SBATCH --mem={kwargs["mem"]}',
        "",
        "set -eu",
        f'JOB_FOLDERS_FILE="{job_folders_file_path}"',
        'JOB_FOLDER="$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$JOB_FOLDERS_FILE")"',
        'cd "$JOB_FOLDER"',
        f"exec {job_runner_command} . --backend slurm",
        "",
    ]
    return lines


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test113_slurm")
    shutil.rmtree(paths.output, ignore_errors=True)
    is_ok = True

    sim = build_simple_simulation(paths.output / "slurm_input")
    split_root = gate.jobs_split(
        sim, 2, paths.output / "slurm_campaign", policy="split_time"
    )

    # Realistic example for manual usage against a Slurm installation:
    #
    # "submit_binary", "submit_filename", and "job_folders_filename" are shown
    # explicitly here for clarity, but in normal usage they can be omitted
    # because the defaults are already "sbatch", "slurm_jobs.sh", and
    # "slurm_job_folders.txt".
    #
    # summary = gate.jobs_run(
    #     split_root,
    #     backend="slurm",
    #     backend_options={
    #         "submit_binary": "sbatch",
    #         "submit_filename": "slurm_jobs.sh",
    #         "job_folders_filename": "slurm_job_folders.txt",
    #         "submit_script_renderer": my_slurm_renderer,
    #         "submit_script_renderer_kwargs": {
    #             "job_runner_command": "opengate_job_runner",
    #             "partition": "cpu",
    #             "cpus_per_task": "4",
    #             "mem": "8G",
    #             "time": "00:30:00",
    #         },
    #         "command_line_args": ["--job-name", "gate_jobs"],
    #     },
    # )
    #
    # This test deliberately does not require a real Slurm installation.
    # Instead of calling sbatch, it uses a benign local command that prints the
    # script filename it receives. This lets us test script rendering and
    # submission command plumbing deterministically.
    summary = gate.jobs_run(
        split_root,
        backend="slurm",
        backend_options={
            "submit_binary": "python3",
            "command_line_args": [
                "-c",
                "import pathlib, sys; print(pathlib.Path(sys.argv[-1]).name)",
            ],
            "submit_filename": "gate_slurm.sh",
            "job_folders_filename": "gate_slurm_job_folders.txt",
            "submit_script_renderer": render_test_slurm_submit_script,
            "submit_script_renderer_kwargs": {
                "job_runner_command": "opengate_job_runner",
                "partition": "cpu",
                "cpus_per_task": "4",
                "mem": "8G",
            },
        },
    )

    submit_file_path = Path(summary["submit_file_path"])
    submit_file_content = submit_file_path.read_text()
    job_folders_file_path = Path(summary["job_folders_file_path"])
    job_folders_file_content = job_folders_file_path.read_text()

    is_ok = is_ok and utility.print_test(
        summary["backend"] == "slurm"
        and summary["submitted_jobs"] == 2
        and summary["skipped_completed_jobs"] == 0
        and summary["campaign_process_pid"] is None,
        f"slurm submission summary: {summary}",
    )

    backend_status = load_backend_status(split_root)
    is_ok = is_ok and utility.print_test(
        backend_status is not None
        and backend_status["backend"] == "slurm"
        and backend_status["status"] == "submitted"
        and backend_status["submitted_jobs"] == 2
        and backend_status["submit_file_path"] == str(submit_file_path)
        and backend_status["scheduler_job_id"] is None,
        f"slurm backend status: {backend_status}",
    )

    is_ok = is_ok and utility.print_test(
        submit_file_path.name == "gate_slurm.sh"
        and summary["submission_stdout"].strip() == "gate_slurm.sh",
        f"slurm submit command output: {summary['submission_stdout'].strip()}",
    )

    is_ok = is_ok and utility.print_test(
        "#!/bin/sh" in submit_file_content
        and "#SBATCH --partition=cpu" in submit_file_content
        and "#SBATCH --cpus-per-task=4" in submit_file_content
        and "#SBATCH --mem=8G" in submit_file_content,
        f"slurm submit script commands:\n{submit_file_content}",
    )

    is_ok = is_ok and utility.print_test(
        'cd "$JOB_FOLDER"' in submit_file_content
        and "exec opengate_job_runner . --backend slurm" in submit_file_content
        and "SLURM_ARRAY_TASK_ID" in submit_file_content,
        f"slurm script execution block:\n{submit_file_content}",
    )

    is_ok = is_ok and utility.print_test(
        str((split_root / "job0001").resolve()) in job_folders_file_content
        and str((split_root / "job0002").resolve()) in job_folders_file_content,
        "slurm job folder list contains both job folders",
    )

    is_ok = is_ok and utility.print_test(
        "--array=0-1" in " ".join(summary["submission_command"]),
        f"slurm submission command: {summary['submission_command']}",
    )

    utility.test_ok(is_ok)

#!/usr/bin/env python3

import json
import shlex
import sys
from pathlib import Path

import click
import colored
import opengate_core as g4
from opengate.exception import color_error, GateMergeError
from opengate.jobs import (
    DEFAULT_JOBS_BACKEND_OPTIONS_FILENAME,
    DEFAULT_SPLIT_POLICY,
    JOBS_MANIFEST_FILENAME,
    _format_bytes as format_bytes,
    _format_count as format_count,
    _format_duration as format_duration,
    JOB_LOG_FILENAME,
    jobs_clean_split,
    jobs_merge,
    jobs_cancel,
    jobs_run,
    jobs_split,
    jobs_status,
    jobs_wait,
)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

BACKENDS = ["local", "htcondor", "slurm", "pbs"]


@click.group(context_settings=CONTEXT_SETTINGS)
def go():
    """Split a simulation into jobs, run them, follow them and merge their output.

    The CAMPAIGN folder contains the simulation.json of the simulation (written
    with sim.to_json_file("campaign/")) and its input files. The most common use,
    on a workstation (split, run with a progress bar, merge; -l: local machine,
    there is no default backend):

        opengate_jobs run campaign/ -j 8 -l

    On a cluster:

    \b
        opengate_jobs split campaign/ -j 100
        opengate_jobs run campaign/ --backend slurm --backend-options options.json
        opengate_jobs status campaign/
        opengate_jobs cancel campaign/     (if needed)
        opengate_jobs merge campaign/
        opengate_jobs clean campaign/
    """


def campaign_argument(f):
    return click.argument("campaign", type=click.Path(exists=True, file_okay=False))(f)


def json_option(f):
    return click.option(
        "--json", "as_json", is_flag=True, help="Print the result as JSON."
    )(f)


def echo_json(data):
    click.echo(json.dumps(data, indent=2, sort_keys=True, default=str))


def short(path):
    """A path relative to the current folder if it is inside, else absolute"""
    path = Path(path).resolve()
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def is_split(campaign):
    return (Path(campaign) / JOBS_MANIFEST_FILENAME).exists()


def do_split(campaign, jobs, policy, link_files, overwrite):
    m = jobs_split(
        simulation_folder=Path(campaign),
        campaign_dir=Path(campaign),
        number_of_jobs=jobs,
        policy=policy,
        link_files=link_files,
        overwrite_existing_job_folders=overwrite,
        write_resolved_simulation=True,
    )
    return m


def split_options(f):
    f = click.option(
        "--overwrite",
        is_flag=True,
        help="Replace the jobs of a campaign already split.",
    )(f)
    f = click.option(
        "--link-files/--copy-files",
        default=False,
        show_default=True,
        help="Link the input files in the job folders instead of copying them.",
    )(f)
    f = click.option(
        "--policy",
        default=DEFAULT_SPLIT_POLICY,
        show_default=True,
        type=click.Choice(["split_in_time_total", "split_in_time_per_run"]),
        help="How the simulation time is split into jobs.",
    )(f)
    return f


def clean_campaign(campaign, remove_job_folders=True, remove_metadata_files=True):
    return jobs_clean_split(
        Path(campaign),
        remove_job_folders=remove_job_folders,
        remove_backend_status=remove_metadata_files,
        remove_execution_status=remove_metadata_files,
        remove_manifest=remove_metadata_files,
        remove_resolved_simulation=remove_metadata_files,
    )


# ---------------------------------------------------------------------------
# split


@go.command(context_settings=CONTEXT_SETTINGS)
@campaign_argument
@click.option("-j", "--jobs", type=int, required=True, help="Number of jobs.")
@split_options
@json_option
def split(campaign, jobs, policy, link_files, overwrite, as_json):
    """Split the simulation of CAMPAIGN into job folders."""
    m = do_split(campaign, jobs, policy, link_files, overwrite)
    if as_json:
        echo_json(m.split_result)
    else:
        click.echo(f"Split into {jobs_str(jobs)} ({policy}) in {short(m.campaign_dir)}")


# ---------------------------------------------------------------------------
# run


def load_backend_options(campaign, backend, backend_options):
    """The backend and its options: from the command line, or from the file
    jobs_backend_options.json of the campaign folder. No default: an error if
    no backend is given (e.g. not to run all the jobs on the login node of a
    cluster by mistake)."""
    default_path = Path(campaign) / DEFAULT_JOBS_BACKEND_OPTIONS_FILENAME
    path = backend_options
    if path is None and default_path.exists():
        path = default_path
    config = {}
    if path is not None:
        with open(path, "r") as f:
            config = json.load(f)
        if not isinstance(config, dict):
            raise click.ClickException(
                f"The backend options file '{path}' must contain a JSON object."
            )
    if backend is None:
        backend = config.get("backend")
    if backend is None:
        raise click.ClickException(
            "No backend: give it with --backend (e.g. --backend slurm "
            "--backend-options <file.json>), -l for the local machine, or in "
            f"{DEFAULT_JOBS_BACKEND_OPTIONS_FILENAME} in the campaign folder."
        )
    if config.get("backend") not in (None, backend):
        click.echo(
            f"Warning: the backend '{backend}' (command line) replaces the backend "
            f"'{config.get('backend')}' of '{path}' (its options are ignored).",
            err=True,
        )
        return backend, None
    return backend, config.get("backend_options")


def failure_report(status):
    """One line per job not completed: its folder, status and error (the
    traceback is in the job.log file of its folder)"""
    lines = []
    for job in status.get("jobs", []):
        execution_status = job.get("execution_status")
        if execution_status == "completed":
            continue
        folder = Path(status["campaign_dir"]) / job["folder_name"]
        execution_status_data = job.get("execution_status_data") or {}
        error = execution_status_data.get("error_message")
        error = str(error).strip().splitlines()[0] if error else ""
        line = f"  {short(folder)}: {execution_status or 'not run'}"
        if execution_status == "lost":
            minutes = (job.get("seconds_since_last_news") or 0) / 60
            line += f", no news for {minutes:.0f} min (process dead?)"
        if error:
            line += f", {error}"
        scheduler_job_id = execution_status_data.get("scheduler_job_id")
        if scheduler_job_id is not None:
            line += f", scheduler job {scheduler_job_id}"
        if (folder / JOB_LOG_FILENAME).exists():
            line += f" (see {short(folder / JOB_LOG_FILENAME)})"
        lines.append(line)
    return "\n".join(lines)


def jobs_str(n):
    return f"{n} job" + ("s" if n != 1 else "")


def counts_str(status):
    c = status.get("execution_counts", {})
    s = f"{c.get('completed', 0)} completed"
    for k in ("failed", "lost", "interrupted", "cancelled", "running", "submitted"):
        if c.get(k, 0) > 0:
            s += f", {c[k]} {k}"
    return s


@go.command(context_settings=CONTEXT_SETTINGS)
@campaign_argument
@click.option(
    "-j",
    "--jobs",
    type=int,
    default=None,
    help="Number of jobs. Needed if CAMPAIGN is not split yet (then it is split first).",
)
@click.option(
    "--backend",
    default=None,
    type=click.Choice(BACKENDS, case_sensitive=False),
    help="Where the jobs run (required: no default), or the backend of "
    "jobs_backend_options.json in CAMPAIGN.",
)
@click.option(
    "-l",
    "--local",
    is_flag=True,
    help="Run the jobs on the local machine (same as --backend local).",
)
@click.option(
    "--backend-options",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="JSON file with the backend and its options "
    "(default: jobs_backend_options.json in CAMPAIGN).",
)
@click.option(
    "--submit-args",
    default=None,
    help="Options added to the submit command of a scheduler backend, e.g. "
    "--submit-args '--time=04:00:00 --cpus-per-task=2' for slurm (they replace "
    "the #SBATCH lines of the submitted file).",
)
@click.option(
    "--workers",
    type=int,
    default=None,
    help="Local backend: number of jobs run at the same time "
    "(default: all the jobs, at most the number of cores / threads per job).",
)
@click.option(
    "--merge/--no-merge",
    default=True,
    show_default=True,
    help="Local backend: merge the output of the jobs at the end.",
)
@click.option(
    "--clean",
    is_flag=True,
    help="Local backend: remove the job folders and the jobs files after the merge.",
)
@click.option(
    "--rerun-completed", is_flag=True, help="Run again the jobs already completed."
)
@click.option(
    "--rerun-running",
    is_flag=True,
    help="Run again the jobs marked as running or submitted (the lost jobs, "
    "without news for a long time, are always run again).",
)
@split_options
@json_option
def run(
    campaign,
    jobs,
    backend,
    local,
    backend_options,
    submit_args,
    workers,
    merge,
    clean,
    rerun_completed,
    rerun_running,
    policy,
    link_files,
    overwrite,
    as_json,
):
    """Run the jobs of CAMPAIGN (split it first if needed, with -j).

    With the local backend (default), wait for the jobs with a progress bar
    (the output of each job is in job.log in its folder), then merge their
    output. With a cluster backend, submit the jobs and return: follow them
    with 'opengate_jobs status', then 'opengate_jobs merge'.
    """
    campaign = Path(campaign).resolve()
    if local:
        if backend not in (None, "local"):
            raise click.ClickException(f"-l (local) and --backend {backend}.")
        backend = "local"
    backend, options = load_backend_options(campaign, backend, backend_options)
    local = backend == "local"
    if submit_args:
        if local:
            raise click.ClickException("--submit-args is not for the local backend.")
        options = dict(options or {})
        options["command_line_args"] = list(
            options.get("command_line_args", [])
        ) + shlex.split(submit_args)

    # split if needed
    if not is_split(campaign) or overwrite:
        if jobs is None:
            what = "is not split yet" if not is_split(campaign) else "is split again"
            raise click.ClickException(
                f"'{short(campaign)}' {what}: give the number of jobs with -j."
            )
        do_split(campaign, jobs, policy, link_files, overwrite)
        if not as_json:
            click.echo(f"Split into {jobs_str(jobs)} ({policy}) in {short(campaign)}")
    elif jobs is not None:
        n = jobs_status(campaign, check_inputs=False)["number_of_jobs"]
        if n != jobs:
            raise click.ClickException(
                f"'{short(campaign)}' is already split into {n} jobs, not {jobs}. "
                f"Use --overwrite to split it again."
            )

    if not local and workers is not None:
        raise click.ClickException("--workers is only for the local backend.")
    result = jobs_run(
        campaign,
        backend=backend,
        backend_options=options,
        number_of_workers=workers,
        force_rerun_completed=rerun_completed,
        allow_rerun_running=rerun_running,
    )

    # cluster: submitted, nothing more to do here
    if not local:
        if as_json:
            echo_json(result)
        else:
            command = result.get("submission_command")
            if command:
                click.echo(f"Submit command (first job): {shlex.join(command)}")
            click.echo(
                f"{jobs_str(result['submitted_jobs'])} submitted to {backend} "
                f"({result['skipped_completed_jobs']} already completed). "
                f"Follow them with: opengate_jobs status {short(campaign)}"
            )
        return

    # local: wait for the jobs
    if result["submitted_jobs"] > 0:
        if not as_json:
            click.echo(
                f"Running {jobs_str(result['submitted_jobs'])} (output in "
                f"{Path(short(campaign)) / 'job*' / 'job.log'})"
            )
        try:
            status = jobs_wait(campaign, progress_bar=not as_json)
        except KeyboardInterrupt:
            click.echo(
                f"\nInterrupted by the user. The completed jobs are kept; run the "
                f"others with: opengate_jobs run {short(campaign)} -l",
                err=True,
            )
            sys.exit(130)
    else:
        status = jobs_status(campaign, check_inputs=False)
    result["jobs"] = counts_str(status)

    total = status["summary_counts"]["total"]
    completed = status.get("execution_counts", {}).get("completed", 0)
    if completed != total:
        if as_json:
            echo_json(result)
        click.echo(
            f"Not all jobs completed ({counts_str(status)}):\n"
            f"{failure_report(status)}",
            err=True,
        )
        sys.exit(1)
    if not as_json:
        click.echo(f"Jobs: {counts_str(status)}")

    if merge:
        m = do_merge(campaign, None, False, command="opengate_jobs merge")
        result["merge"] = merge_summary(m)
        if not as_json:
            echo_merge(m)
        if clean:
            result["clean"] = clean_campaign(campaign)
            if not as_json:
                click.echo("Job folders and jobs files removed")
    if as_json:
        echo_json(result)


# ---------------------------------------------------------------------------
# merge


def do_merge(campaign, output, force, command=None):
    """Merge, refused if the output folder contains the merge of another
    campaign or other output files (unless force)."""
    try:
        m = jobs_merge(Path(campaign), to_path=output, execute=False)
        reason = m.check_merged_output_dir()
        if reason is not None and not force:
            what = "--force" if command is None else f"'{command} --force'"
            raise click.ClickException(
                f"{reason}\nUse another folder (-o), or {what} to overwrite."
            )
        m.merge()
    except GateMergeError as e:
        raise click.ClickException(str(e))
    return m


def merged_output_dir(merge_manager):
    if merge_manager.output_dir_override is not None:
        return Path(merge_manager.output_dir_override).resolve()
    return merge_manager.master_simulation.get_output_path()


def merge_summary(merge_manager):
    return {
        **merge_manager.merge_result,
        "merged_output_dir": str(merged_output_dir(merge_manager)),
    }


def echo_merge(merge_manager):
    n = len(merge_manager.leaf_sources)
    click.echo(
        f"Merged {jobs_str(n)} into {short(merged_output_dir(merge_manager))} "
        f"({merge_manager.total_merge_duration:.1f} s)"
    )


@go.command(context_settings=CONTEXT_SETTINGS)
@campaign_argument
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=False),
    default=None,
    help="Folder of the merged output (default: the output_dir of the simulation).",
)
@click.option(
    "--clean",
    is_flag=True,
    help="Remove the job folders and the jobs files after the merge.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Merge even if the output folder contains the merge of another "
    "campaign, or output files not from a merge of this campaign.",
)
@click.option("-v", "--verbose", is_flag=True, help="Print the full merge summary.")
@json_option
def merge(campaign, output, clean, force, verbose, as_json):
    """Merge the output of the completed jobs of CAMPAIGN.

    The merged output goes to the output_dir of the simulation (or -o), with
    merged_from.json (campaign, simulation id, jobs, events, date). Refused
    if this folder contains the merge of another campaign or other output
    files (--force); merging the same campaign again is allowed."""
    status = jobs_status(campaign, check_inputs=False)
    completed = status.get("execution_counts", {}).get("completed", 0)
    if completed != status["summary_counts"]["total"]:
        raise click.ClickException(
            f"Not all jobs completed ({counts_str(status)}):\n"
            f"{failure_report(status)}"
        )
    m = do_merge(campaign, output, force)
    result = merge_summary(m)
    if clean:
        result["clean"] = clean_campaign(campaign)
    if as_json:
        echo_json(result)
        return
    if verbose:
        m.print_merge_summary()
    echo_merge(m)
    if clean:
        click.echo("Job folders and jobs files removed")


# ---------------------------------------------------------------------------
# cancel


@go.command(context_settings=CONTEXT_SETTINGS)
@campaign_argument
@click.option(
    "--backend-options",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="JSON file of the backend options: 'cancel_binary' replaces the "
    "default command (scancel, qdel, condor_rm).",
)
@json_option
def cancel(campaign, backend_options, as_json):
    """Cancel the submitted and running jobs of CAMPAIGN (all the backends).

    Scheduler (slurm, pbs, htcondor): scancel, qdel or condor_rm with the job
    ids given at the submission. Local: the processes of the campaign and of
    the running jobs are stopped. The jobs are marked 'cancelled'; the
    completed jobs are kept, 'opengate_jobs run' runs the others again."""
    options = None
    if backend_options is not None:
        with open(backend_options) as f:
            options = json.load(f).get("backend_options")
    result = jobs_cancel(campaign, backend_options=options)
    if as_json:
        echo_json(result)
        return
    for command in result["commands"]:
        line = " ".join(command)
        click.echo(line if len(line) < 200 else line[:200] + " ...")
    for w in result["warnings"]:
        click.echo(f"Warning: {w}", err=True)
    n = len(result["cancelled_jobs"])
    if n == 0:
        click.echo("No submitted or running job to cancel")
    else:
        click.echo(
            f"{jobs_str(n)} cancelled. Run them again with: "
            f"opengate_jobs run {short(campaign)} ..."
        )


# ---------------------------------------------------------------------------
# clean


@go.command(context_settings=CONTEXT_SETTINGS)
@campaign_argument
@click.option(
    "--remove-job-folders/--keep-job-folders",
    default=True,
    show_default=True,
    help="Remove the job folders.",
)
@click.option(
    "--remove-metadata-files/--keep-metadata-files",
    default=True,
    show_default=True,
    help="Remove the jobs metadata files of the campaign folder (manifest, status).",
)
@json_option
def clean(campaign, remove_job_folders, remove_metadata_files, as_json):
    """Remove the job folders and the jobs files of CAMPAIGN (simulation.json
    and the merged output are kept)."""
    result = clean_campaign(campaign, remove_job_folders, remove_metadata_files)
    if as_json:
        echo_json(result)
    else:
        click.echo(f"Removed {len(result['removed_paths'])} files or folders")


# ---------------------------------------------------------------------------
# status


def seconds(t):
    """Time in seconds, 4 significant digits (e.g. 54.85, 115.1, 0.001)"""
    return f"{t / g4.G4UnitDefinition.GetValueOf('s'):.4g}"


def runs_str(intervals):
    return f"{len(intervals)} run" + ("s" if len(intervals) > 1 else "")


def best_unit_time(t):
    return str(g4.G4BestUnit(t, "Time")).strip()


def format_campaign_timing(intervals, verbose=False):
    """
    Runs of the whole campaign: the timeline (start of the first run to the end
    of the last one), the total acquisition time (sum of the run durations) and
    the gaps between the runs (nothing is simulated during the gaps).
    With verbose, the list of all the intervals.
    """
    if not intervals:
        return "no runs"
    if verbose:
        return format_all_intervals(intervals)
    start, end = intervals[0][0], intervals[-1][1]
    acquisition = sum(i[1] - i[0] for i in intervals)
    s = (
        f"{runs_str(intervals)}, timeline {seconds(start)} to {seconds(end)} s, "
        f"total acquisition time {seconds(acquisition)} s"
    )
    gaps = end - start - acquisition
    if gaps > 1e-9 * (end - start):
        s += f" (+ {seconds(gaps)} s of gaps between runs)"
    return s


def format_job_timing(intervals, verbose=False):
    """Runs of one job: timeline and acquisition duration (sum of the runs)"""
    if not intervals:
        return "no runs"
    if verbose:
        return format_all_intervals(intervals)
    acquisition = sum(i[1] - i[0] for i in intervals)
    return (
        f"{runs_str(intervals)}, timeline {seconds(intervals[0][0])} to "
        f"{seconds(intervals[-1][1])} s, acquisition duration {seconds(acquisition)} s"
    )


def format_all_intervals(intervals):
    intervals_str = ", ".join(
        f"[{best_unit_time(i[0])}, {best_unit_time(i[1])}]" for i in intervals
    )
    return f"{intervals_str}  {len(intervals)} run(s)"


# above this number of jobs, the status only lists the jobs that need
# attention (all with -v)
MAX_LISTED_JOBS = 20


def job_needs_attention(job):
    return job["status"] != "ready" or job.get("execution_status") in (
        "failed",
        "lost",
        "interrupted",
        "cancelled",
    )


def format_progress(progress):
    return (
        f"{progress['fraction'] * 100:.1f} % of the events "
        f"({format_count(progress['generated_events'])} events)"
    )


def format_estimated_times(progress):
    """One job duration, end of the running jobs, jobs not started: estimated
    from the completed and running jobs (empty if nothing is known yet)"""
    items = []
    job_duration = progress.get("job_duration_seconds")
    if job_duration is not None:
        n = progress.get("number_of_completed_durations", 0)
        source = f"{n} completed" if n > 0 else "running jobs"
        items.append(f"one job ~{format_duration(job_duration)} (from {source})")
    remaining = progress.get("running_remaining_seconds")
    if remaining is not None:
        items.append(f"running jobs end in ~{format_duration(remaining)}")
    not_started = progress.get("not_started", 0)
    if not_started > 0 and items:
        items.append(f"{not_started} not started (depends on the queue)")
    return "; ".join(items)


def print_jobs_status_summary(status_data, verbose=False):
    intervals = status_data.get("original_run_timing_intervals", [])
    print(f" Manifest file:      {status_data['manifest_path']}")
    print(f" Campaign dir:       {status_data['campaign_dir']}")
    print(f" Simulation ID:      {status_data['simulation_id']}")
    print(f" Created at:         {status_data['created_at']}")
    print(f" Split policy:       {status_data['policy']}")
    print(f" Prefer resolved:    {status_data.get('prefer_resolved_simulation', True)}")
    print(f" Number of jobs:     {status_data['number_of_jobs']}")
    print(f" Time intervals:     {format_campaign_timing(intervals, verbose)}")
    master_str = (
        "Found"
        if status_data["master_simulation_exists"]
        else colored.stylize("Missing", color_error)
    )
    print(f" Master simulation:  {master_str}")
    print(f"   Path:             {status_data['master_simulation_path']}")
    resolved_exists = status_data.get("resolved_simulation_exists", False)
    resolved_path = status_data.get("resolved_simulation_path")
    if resolved_path is not None:
        resolved_str = (
            "Found" if resolved_exists else colored.stylize("Missing", color_error)
        )
        print(f" Resolved sim:       {resolved_str}")
        print(f"   Path:             {resolved_path}")
    inputs_checked = status_data.get("inputs_checked", True)
    master_inputs = status_data.get("master_input_files", [])
    if not inputs_checked:
        print(" Master input files: not checked (--check)")
    elif master_inputs:
        print(" Master input files:")
        for item in master_inputs:
            print(
                f"   - [{item['class_name']}] {item['object_name']} -> {item['attribute']}: {item['value']}"
            )
    else:
        print(" Master input files: None")
    print(" Job Status Summary:")
    counts = status_data["summary_counts"]
    missing_total = (
        counts["missing_folder"]
        + counts["missing_metadata"]
        + counts.get("missing_input_file", 0)
    )
    missing_str = (
        colored.stylize(str(missing_total), color_error)
        if missing_total > 0
        else str(missing_total)
    )
    print(
        f"  Total: {counts['total']}  |  Ready: {counts['ready']}  |  Missing: {missing_str}"
    )
    execution_counts = status_data.get("execution_counts", {})
    if len(execution_counts) > 0:
        print(
            "  Execution: "
            f"submitted={execution_counts.get('submitted', 0)}  "
            f"running={execution_counts.get('running', 0)}  "
            f"lost={execution_counts.get('lost', 0)}  "
            f"completed={execution_counts.get('completed', 0)}  "
            f"failed={execution_counts.get('failed', 0)}  "
            f"skipped={execution_counts.get('skipped', 0)}  "
            f"interrupted={execution_counts.get('interrupted', 0)}  "
            f"cancelled={execution_counts.get('cancelled', 0)}"
        )
    progress = status_data.get("progress")
    if progress is not None:
        print(f"  Progress: {format_progress(progress)}")
        estimated = format_estimated_times(progress)
        if estimated:
            print(f"  Estimated: {estimated}")
    last_merge = status_data.get("last_merge")
    if last_merge is not None:
        print(
            f"  Merged: into {last_merge.get('output_dir')} at "
            f"{str(last_merge.get('merged_at', ''))[:16].replace('T', ' ')}"
        )

    jobs = status_data["jobs"]
    inputs_size = sum(job.get("input_files_size_bytes", 0) for job in jobs)
    folders_size = sum(job.get("folder_size_bytes", 0) for job in jobs)
    # the input files are the same for all jobs (one copy or link per job)
    per_job = sorted({job.get("number_of_input_files", 0) for job in jobs})
    per_job_str = (
        str(per_job[0]) if len(per_job) == 1 else f"{per_job[0]} to {per_job[-1]}"
    )
    input_mode = (
        "links" if any(j.get("input_mode") == "linked" for j in jobs) else "copies"
    )
    if inputs_checked:
        print(
            f"  Inputs: {per_job_str} files per job ({input_mode}), "
            f"{format_bytes(inputs_size)} for all the jobs; "
            f"job folders: {format_bytes(folders_size)}"
        )

    # many jobs: only the ones that need attention (all with -v)
    listed = jobs
    if not verbose and len(jobs) > MAX_LISTED_JOBS:
        listed = [j for j in jobs if job_needs_attention(j)]
        print(
            f"  {len(listed)} job(s) listed out of {len(jobs)} (failed, lost, "
            f"interrupted, cancelled or not ready; -v for all)"
        )
    for job in listed:
        job_idx = job["job_index"]
        folder = job["folder_name"]
        st = job["status"].upper()
        st_str = colored.stylize(st, color_error) if st != "READY" else st
        exec_status = job.get("execution_status")
        exec_str = exec_status.upper() if exec_status is not None else "NONE"
        if exec_status in ("running", "lost") and job.get("progress_fraction"):
            exec_str += f" {job['progress_fraction'] * 100:.0f}%"
        if exec_status in ("failed", "lost", "interrupted", "cancelled"):
            exec_str = colored.stylize(exec_str, color_error)
        job_intervals = job.get("run_timing_intervals", [])
        timing_str = format_job_timing(job_intervals, verbose)
        print(
            f"  [Job {job_idx:04d}] {folder}: status = {st_str}, "
            f"execution = {exec_str}, {timing_str}"
        )
        input_check_error = job.get("input_check_error")
        if input_check_error is not None:
            err_msg = f"     Cannot check the input files: {input_check_error}"
            print(colored.stylize(err_msg, color_error))
        missing_files = job.get("missing_input_files", [])
        if missing_files:
            for missing in missing_files:
                err_msg = f"     Missing input file: {missing}"
                print(colored.stylize(err_msg, color_error))


@go.command(context_settings=CONTEXT_SETTINGS)
@campaign_argument
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help=f"List all the jobs (above {MAX_LISTED_JOBS} jobs, only the ones that "
    "need attention are listed) and all the run timing intervals.",
)
@click.option(
    "--check",
    is_flag=True,
    help="Check the input files of each job and compute the size of the job "
    "folders (slow: the simulation of each job is created).",
)
@json_option
def status(campaign, verbose, check, as_json):
    """Print the status of the jobs of CAMPAIGN."""
    status_data = jobs_status(campaign, check_inputs=check)
    if as_json:
        echo_json(status_data)
    else:
        print_jobs_status_summary(status_data, verbose=verbose)


if __name__ == "__main__":
    go()

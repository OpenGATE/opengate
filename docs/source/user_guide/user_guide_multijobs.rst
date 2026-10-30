Multi-job execution
===================

GATE can split one simulation into several child jobs, run those jobs, and merge
their output again. This is useful in two main situations:

- local execution on a workstation, where several jobs can run in parallel on
  the same machine
- server execution, where the split jobs are submitted to a scheduler such as
  Slurm, HTCondor or PBS.

This section focuses on the current user-facing workflow in GATE 10.


Local multi-job execution
-------------------------

For local execution, the recommended entry point is ``sim.run(...)`` with the
``number_of_jobs`` argument. GATE then:

1. resolves and splits the simulation into child jobs
2. runs the jobs through a local process pool
3. optionally merges the result back into the live simulation object


Run split, execution, and merge in one go
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the goal is to run locally and immediately continue with postprocessing in
the same script, use ``merge_after_run=True`` together with
``wait_for_result=True``.

.. code-block:: python

   import opengate as gate

   sim = gate.Simulation()
   sim.output_dir = "output"

   # ... configure geometry, physics, sources, and actors ...

   controller = sim.run(
       number_of_jobs=4,
       wait_for_result=True,
       merge_after_run=True,
   )

   # At this point, the merged output is already available in sim.output_dir
   # and the live simulation object can be used for postprocessing.

In the example, ``controller`` is a ``SplitRunMergeController`` object that can be inspected. It is always returned by ``sim.run(...)`` when the simulation is run in multiple jobs.

Local pooled execution always uses one spawned worker process per child job.
The output of each job (the messages of GATE and Geant4) goes to the file
``job.log`` in its folder, not to the terminal.

With ``sim.progress_bar = True``, a single progress bar shows the progress of all
the jobs while ``sim.run(...)`` waits for them (the jobs do not display their own
progress bars, they would all print in the same terminal). Each job writes its
number of generated and expected events in ``job_progress.json``, in its folder.

.. note:: ``number_of_jobs=1`` does not create a split campaign. It maps to an ordinary simulation run in a new process, i.e. it is equivalent to ``sim.run(start_new_process=True)``

Split and run now, merge later
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes it is preferable to separate execution and merging. A typical
example is a long local run that should finish first, while merging and
postprocessing happen only afterwards, possibly in another script.

The first script can launch the split jobs and stop after execution:

.. code-block:: python

   import opengate as gate

   sim = gate.Simulation()
   sim.output_dir = "output"

   # ... configure geometry, physics, sources, and actors ...

   controller = sim.run(
       number_of_jobs=4,
       wait_for_result=False,
       merge_after_run=False,
       campaign_dir="campaign",
   )

   print(controller.stage)         # typically "submitted"
   print(controller.campaign_dir) # folder containing simulation.json and job0001, job0002, ...

Later, another script can re-use the campaign folder and merge the finished
jobs:

.. code-block:: python

   import opengate as gate

   merge_manager = gate.jobs_merge("campaign")
   sim = merge_manager.master_simulation
   gate.jobs_clean_split("campaign")  # this removes the job folders and other metadata about the split run

   merge_manager.print_merge_summary()
   # ... post-process sim, actors, and merged output ...

In this scenario, merging recreates a simulation from the files in the
campaign folder and writes merged output to the configured output directory of
that simulation.

Low-level split, run, and merge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The lower-level functions can also be called explicitly. ``jobs_split(...)``
returns a ``JobsSplitManager`` object; use ``jobs_split_manager.campaign_dir`` when
passing the campaign folder to the next stage.

.. code-block:: python

   import opengate as gate

   sim = gate.Simulation()
   sim.output_dir = "output"

   # ... configure geometry, physics, sources, and actors ...

   jobs_split_manager = gate.jobs_split(
       simulation=sim,
       campaign_dir="campaign",
       number_of_jobs=4,
       policy="split_in_time_total",
   )

   # local_pool is the default backend; jobs_run returns while the jobs run
   run_summary = gate.jobs_run(jobs_split_manager.campaign_dir)
   # wait for the end of the jobs (with a progress bar in a terminal)
   gate.jobs_wait(jobs_split_manager.campaign_dir)

   merge_manager = gate.jobs_merge(jobs_split_manager.campaign_dir)
   merged_sim = merge_manager.master_simulation


Split policies
~~~~~~~~~~~~~~

GATE currently provides two time-based split policies.

``split_in_time_total``
   This is the default policy. It splits the total active simulation time into
   several consecutive jobs of similar duration. A child job may therefore
   bridge across two original run timing intervals. This is usually the best
   starting point for local acceleration and for general split campaigns.

``split_in_time_per_run``
   This policy splits each original run timing interval separately. The number
   of jobs must then be a multiple of the number of original runs. Use this
   when the split should remain more directly aligned with the original run
   structure.

Choose the policy explicitly with the ``split_policy`` argument:

.. code-block:: python

   import opengate as gate

   sim = gate.Simulation()

   # ... configure geometry, sources, actors, and run_timing_intervals ...

   controller_total = sim.run(
       number_of_jobs=4,
       split_policy="split_in_time_total",
       wait_for_result=True,
       merge_after_run=True,
   )

   controller_per_run = sim.run(
       number_of_jobs=4,
       split_policy="split_in_time_per_run",
       wait_for_result=True,
       merge_after_run=True,
   )

In practice, ``split_in_time_total`` is the recommended default unless the
simulation logic or the validation strategy specifically benefits from staying
closer to the original run partition.

.. tip:: If you use ``split_in_time_per_run`` and set the number of jobs equal to the number of run timing intervals in your simulation, you will get one job per run timing interval.


Local multi-job execution from the command line
-----------------------------------------------

The simulation can also be written in a campaign folder and run with the
``opengate_jobs`` command. In the script, replace ``sim.run()`` by:

.. code-block:: python

   sim.to_json_file("campaign/")

Then, in one command, split the simulation into 8 jobs, run them on the local
machine (``-l``, with one progress bar for all the jobs) and merge their
output:

.. code-block:: console

   opengate_jobs run campaign/ -j 8 -l

There is no default backend: ``-l`` (or ``--backend local``) is required to run
the jobs on the local machine, so that the jobs of a campaign are not run on
the login node of a cluster by mistake.

The merged output is written in the ``output_dir`` of the simulation. A
relative ``output_dir`` is relative to the campaign folder, e.g.
``campaign/output`` for ``sim.output_dir = "output"``.

- The output of each job is in ``campaign/job000N/job.log``.
- If some jobs fail or are interrupted (Control-C), the command reports them
  and does not merge. Run the same command again to run only the jobs that did
  not complete; the completed jobs are kept.
- ``--workers N`` runs at most N jobs at the same time (all the jobs by
  default).
- ``--no-merge`` does not merge; ``--clean`` removes the job folders after the
  merge.
- ``-j`` is only needed the first time (to split). To split again with another
  number of jobs, add ``--overwrite``.


Server-based execution
----------------------

Server-based multi-job execution is intended to be file-based:

1. prepare a campaign folder containing ``simulation.json`` and the required
   input files, probably locally. To create the ```simulation.json`` file, you can use ``sim.to_json_file()`` in your script instead of ``sim.run(...)``.
2. transfer the campaign folder to the server. Be aware of the paths used in the .json file for material database or other input files. They should be valid on the server.
3. split the simulation on the server
4. submit the child jobs through a scheduler
5. inspect job status
6. merge the finished jobs
7. optionally clean temporary split artifacts
8. transfer the campaign folder with the merged output back to your local machine

.. warning::

   Server-based multi-job execution is currently untested. The workflow and
   command-line tools are available, but they should still be treated as
   experimental until broader validation has been completed.


Suggested server workflow
~~~~~~~~~~~~~~~~~~~~~~~~~

On a large server, execution of simulations is usually handled via :ref:`command-line tools <command_line_tools>`.

Assume a campaign folder called ``campaign`` containing:

- ``simulation.json``
- any input files needed by the simulation

Then the workflow is:

.. code-block:: console

   opengate_jobs split campaign/ -j 100
   opengate_jobs run campaign/ --backend htcondor --backend-options htcondor_options.json
   opengate_jobs status campaign/
   opengate_jobs merge campaign/
   opengate_jobs clean campaign/

The campaign folder is the authoritative container throughout the workflow. It
contains:

- the master ``simulation.json``
- optionally ``simulation_resolved.json``
- the child folders ``job0001``, ``job0002``, ...
- the manifest and status files used by the jobs tools
- the merged output


Backend options on a server
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``opengate_jobs run`` command accepts the backend explicitly and can read
backend options from a JSON file:

.. code-block:: console

   opengate_jobs run campaign/ --backend htcondor --backend-options htcondor_options.json

As a convenience, the command also looks for a default file named
``jobs_backend_options.json`` inside the campaign folder when no
``--backend-options`` argument is provided. Without backend (on the command
line or in this file), ``run`` refuses to run the jobs.

With slurm, each job is submitted with ``sbatch <command_line_args>
--export=ALL,JOBDIR=<job folder> <submit_filename>`` (``JOBDIR`` is added to
the ``--export`` option if ``command_line_args`` has one). The options of one
campaign can be added on the command line, e.g. the time limit and the
number of cores per job:

.. code-block:: console

   opengate_jobs run campaign/ --backend-options slurm_options.json --submit-args "--time=04:00:00 --cpus-per-task=2"

They replace the ``#SBATCH`` lines of the submitted file. ``run`` prints the
submit command of the first job, and warns if the number of cores per job
(``--cpus-per-task``) differs from the number of threads of the simulation.

With a scheduler backend, ``opengate_jobs run`` only submits the jobs and
returns: follow them with ``opengate_jobs status campaign``, and merge them
with ``opengate_jobs merge campaign`` once they are all completed (the merge
refuses an incomplete campaign).


Following the jobs
~~~~~~~~~~~~~~~~~~

``opengate_jobs status campaign`` only reads the files of the campaign (it does
not query the scheduler), so it works the same for all the backends. The
execution state of each job is one of:

- ``submitted``: submitted by ``opengate_jobs run``, not started yet (waiting
  in the queue of the scheduler, or for a local worker). The id given by the
  scheduler is kept in ``job_execution_status.json`` (e.g. for ``sacct``).
- ``running``: started. During the simulation, the job writes its progress in
  ``job_progress.json`` (every 2 s with a local backend, 60 s with a scheduler).
- ``lost``: running, but without news for more than 10 min while simulating
  events (1 h during the initialization or the writing of the output): its
  process died without reporting, e.g. killed by the scheduler (time limit,
  memory) or crashed. The cause is in the log of the scheduler.
- ``completed``, ``failed`` (the error is in ``job_execution_status.json`` and
  in the log of the job), ``interrupted`` (Control-C, local backends).

Run ``opengate_jobs run campaign`` again to submit the jobs that did not
complete (failed, interrupted, lost); the completed jobs are kept. ``run``
refuses while some jobs are still ``submitted`` or ``running``
(``--rerun-running`` to submit them anyway, e.g. for a job removed from the
queue of the scheduler, which stays ``submitted``).

``status`` also gives the progress of the campaign (fraction of the events,
the jobs being of equal size) and estimated times: the duration of one job
(mean of the completed jobs, or from the running ones), and the end of the
running jobs. The start of the jobs not started depends on the queue of the
scheduler, it is not estimated. Above 20 jobs, only the jobs that need
attention (failed, lost, interrupted, not ready) are listed; ``-v`` lists all
of them.

By default, ``status`` does not check the input files of the jobs (fast, even
with hundreds of jobs). ``opengate_jobs status campaign --check`` also checks
that the input files of each job are found and gives the size of the job
folders (slow: the simulation of each job is created).

The merge only needs the actors of the simulations and the output of the jobs,
not their input files: a campaign can be merged after being moved to another
folder or computer, e.g. ``opengate_jobs merge campaign -o merged``.

You can find examples you can adapt in the ``contrib/cluster`` folder for slurm and pbs backends.
The backend options are usually site-specific and should be adapted to the target server.


.. Example: Slurm
.. ~~~~~~~~~~~~~~

.. The Slurm backend currently expects a Python callable named
.. ``submit_script_renderer``. This means that, at the moment, Slurm submission is
.. best driven from a Python script rather than through a pure JSON configuration
.. file. This will likely change in the future.

.. A minimal Python example looks like:

.. .. code-block:: python

..    import opengate as gate

..    def my_slurm_renderer(job_folders_file_path, **kwargs):
..        return [
..            "#!/bin/sh",
..            "#SBATCH --partition=cpu",
..            "#SBATCH --cpus-per-task=4",
..            "#SBATCH --mem=8G",
..            "",
..            "set -eu",
..            f'JOB_FOLDERS_FILE="{job_folders_file_path}"',
..            'JOB_FOLDER="$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$JOB_FOLDERS_FILE")"',
..            'cd "$JOB_FOLDER"',
..            "exec opengate_job_runner . --backend slurm",
..        ]

..    gate.jobs_run(
..        "campaign",
..        backend="slurm",
..        backend_options={
..            "submit_script_renderer": my_slurm_renderer,
..            "submit_script_renderer_kwargs": {},
..            "command_line_args": ["--job-name", "gate_jobs"],
..        },
..    )

.. This explicit renderer is intentional for now because Slurm setups are often
.. site-specific.


Example: HTCondor
~~~~~~~~~~~~~~~~~

A possible HTCondor backend options file could look like:

.. code-block:: json

   {
     "backend": "htcondor",
     "backend_options": {
       "submit_file_commands": {
         "request_memory": "8 GB",
         "request_cpus": "4"
       },
       "command_line_args": ["-batch-name", "gate_jobs"]
     }
   }

The actual submission requirements are often site-dependent. The
backend options should therefore be adapted to the target server.


.. _command_line_tools:

Command-line tools
------------------

GATE ships with one multi-job command-line tool, ``opengate_jobs``, with the
subcommands:

- ``opengate_jobs run``: run the jobs of a campaign through a backend (required:
  ``-l`` for the local machine, ``--backend``, ``--backend-options``), after
  splitting it if needed (``-j``); with the local backend, wait
  for the jobs and merge their output
- ``opengate_jobs split``: split a campaign folder into child jobs
- ``opengate_jobs status``: inspect the current campaign status (``--check``
  to also check the input files of the jobs)
- ``opengate_jobs merge``: merge the finished jobs (``-o`` for another output
  folder)
- ``opengate_jobs clean``: remove the job folders and the jobs files

Use ``opengate_jobs <subcommand> -h`` for all the options. ``--json`` prints
the result as JSON, for scripts.

``opengate_job_runner`` executes one individual child job folder: it is mainly
useful for scheduler payload commands. End users will usually work with
``opengate_jobs`` instead.

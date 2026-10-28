Multi-job execution
===================

GATE can split one simulation into several child jobs, run those jobs, and merge
their output again. This is useful in two main situations:

- local execution on a workstation, where several jobs can run in parallel on
  the same machine
- server execution, where the split jobs are submitted to a scheduler such as
  Slurm or HTCondor

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
   gate.jobs_clean("campaign")  # this removes the job folders and other metadata about the split run

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

   run_summary = gate.jobs_run(
       jobs_split_manager.campaign_dir,
       backend="local_pool",
   )

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


Server-based execution
----------------------

Server-based multi-job execution is intended to be file-based:

1. prepare a campaign folder containing ``simulation.json`` and the required
   input files, probably locally
2. transfer the campaign folder to the server
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

   opengate_jobs_split campaign --number-of-jobs 100
   opengate_jobs_run campaign --backend htcondor --backend-options-json htcondor_options.json
   opengate_jobs_status campaign
   opengate_jobs_merge campaign
   opengate_jobs_clean campaign

The campaign folder is the authoritative container throughout the workflow. It
contains:

- the master ``simulation.json``
- optionally ``simulation_resolved.json``
- the child folders ``job0001``, ``job0002``, ...
- the manifest and status files used by the jobs tools
- the merged output


Backend options on a server
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``opengate_jobs_run`` command accepts the backend explicitly and can read
backend options from a JSON file:

.. code-block:: console

   opengate_jobs_run campaign --backend htcondor --backend-options-json htcondor_options.json

As a convenience, the command also looks for a default file named
``jobs_backend_options.json`` inside the campaign folder when no
``--backend-options-json`` or ``--backend`` argument is provided.


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

GATE ships with multi-job command-line tools mainly intended for handling simulations on servers:

- ``opengate_jobs_split``: split a campaign folder into child jobs
- ``opengate_jobs_run``: launch a split campaign through a backend
- ``opengate_jobs_status``: inspect the current campaign status
- ``opengate_jobs_merge``: merge the finished jobs
- ``opengate_jobs_clean``: remove temporary split-job artifacts
- ``opengate_job_runner``: execute one individual child job folder

The single-job runner is mainly useful for scheduler payload commands. End
users will usually work with the campaign-level commands instead.

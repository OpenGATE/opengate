Multi job architecture
======================

This chapter gives developers background information about the multi-job
execution architecture. The user-facing documentation explains how to run
multi-job simulations. This page focuses on the internal contracts that make
splitting, execution, and merging work together.

The central design choice is that a split campaign is file based. Each job is a
self-contained simulation folder with its own ``simulation.json``, input files or
links, output folder, and status files. Worker processes never receive live
``Simulation`` instances from the parent Python process. They rehydrate a
simulation from disk and run it in their own process.


Workflows
---------

Split
^^^^^

The split phase is coordinated by ``JobsSplitManager`` and exposed through
``gate.jobs_split(...)``. The manager prepares an authoritative campaign
representation before creating child jobs:

1. A master simulation is created from either a live ``Simulation`` object or a
   packaged ``simulation.json``.
2. ``resolve_and_validate_config(context="split_preparation")`` is called on the
   master simulation. This stage is allowed to mutate user info if values need
   to be resolved before cloning, for example run timing dependent dynamic
   parametrisations.
3. The resolved master configuration is stored in the campaign folder.
4. Child simulations are cloned from the resolved master dictionary.
5. Each child receives job-specific changes, such as run timing intervals and
   random seed updates.
6. Input files are transferred into each job folder by copy or symlink, and the
   child ``simulation.json`` is rewritten so rehydrated paths point to the
   job-local files.
7. The campaign manifest and one metadata file per job are written.

The manifest is the campaign-level index. It records the original run timing
intervals, the split policy, the authoritative simulation file names, and the
list of jobs. Each job metadata file records the mapping between local run
indices in the child simulation and original run indices in the master
simulation.

The current split policies are:

``split_in_time_per_run``
    Split each original run interval independently. This keeps every job inside
    one original run.

``split_in_time_total``
    Split the total simulation time into equal-duration jobs. A child job may
    bridge more than one original run, so its local run timing intervals may map
    to different original run indices.

Run
^^^

The run phase is exposed through ``gate.jobs_run(...)`` and can use different
backends. The local backends are:

``local_sequential``
    Run the job folders one after another. This backend is mainly useful for
    testing and debugging orchestration.

``local_pool``
    Run job folders through a local process pool. The process start method is
    ``spawn`` by contract, because Geant4 state must not be inherited through
    ``fork``. Each worker process runs one Geant4 simulation and exits.

Scheduler backends such as HTCondor and SLURM submit the same file-based job
folders to an external queueing system. GATE generates the submission files and
commands, but deliberately keeps backend-specific options transparent so users
can pass scheduler options in the form expected by their site.

Every job writes ``job_execution_status.json`` in its job folder. This file is
the authoritative execution status for recovery and reruns. Campaign-level
backend submission metadata is stored separately.

Merge
^^^^^

The merge phase is coordinated by ``JobsMergeManager`` and exposed through
``gate.jobs_merge(...)``. The manager rehydrates the master simulation and the
child simulations from disk, builds a ``MergeContext``, executes the merge, and
finalizes output writing.

The workflow is split into three stages:

``plan_merge()``
    Rehydrate the simulations, collect one output-level contribution plan per
    source simulation, enrich the plans with local-to-original run mappings, and
    create merge coordinators.

``execute_merge()``
    Ask the target simulation to execute the prepared coordinators. Standard
    output and ROOT output are handled by different coordinators because ROOT
    files may be shared by several actor outputs.

``finalize_merge()``
    Finish writes, close data, emit warnings for unmergeable output, and build
    the result summary.

The merge context contains both informative and instructive data. The
local-to-original run mapping is informative and campaign-global. The output
contribution inventory is instructive: it says which output item from which
source job contributes to which target slot.


User-facing Python API, CLI, and internal wiring
------------------------------------------------

There are three public layers over the same implementation:

``sim.run(number_of_jobs=N, ...)``
    High-level local API. This creates a ``SplitRunMergeController`` and uses it
    to split, run, and optionally merge the simulation. This is the natural path
    for local multi-job execution.

``SplitRunMergeController``
    Python API object for local workflows that need more control than a single
    ``sim.run(...)`` call. It exposes workflow state, status refresh, and access
    to the split and merge managers.

``gate.jobs_split(...)``, ``gate.jobs_run(...)``, ``gate.jobs_merge(...)``
    Lower-level file-based entry points. These are used directly by scripts,
    tests, and command line tools.

The CLI tools call the same lower-level functions. This is important for server
usage: the user can package a simulation folder, copy it to a cluster, then run
``opengate_jobs_split``, ``opengate_jobs_run``, ``opengate_jobs_merge``, and
``opengate_jobs_clean`` without writing a custom Python driver script on the
cluster.


Simulation stages: resolve_and_validate_config vs initialize
------------------------------------------------------------

``resolve_and_validate_config()`` is a Python configuration stage. It is allowed
to resolve interdependent user info entries, validate references, fill derived
configuration, and make the configuration serializable. It must not require an
initialized Geant4 run manager.

``initialize()`` is a runtime initialization stage. It should prepare C++ state,
Geant4 registrations, and runtime objects that are meaningful only when the
simulation engine is being initialized.

This distinction is essential for job splitting. The splitter must prepare child
``simulation.json`` files before those children are ever run. Any configuration
that depends on the child's timing structure, dynamic parametrisation, input
file transfer, or output configuration must therefore be resolved before runtime
initialization.

When adding new components, developers should ask:

* Does this operation only interpret or validate Python configuration? Put it in
  ``resolve_and_validate_config()``.
* Does this operation communicate with Geant4 or depend on initialized C++ state?
  Keep it in ``initialize()`` or a runtime hook.
* Does this operation depend on split-job timing? Resolve it before writing the
  child ``simulation.json``.


Contract: actor - actor_output - data_container/data_items
----------------------------------------------------------

Actors own actor output objects. Actor output objects own data containers. Data
containers own data items. This hierarchy is the merge contract.

Actors should not implement ad-hoc merge logic for files they produce. Instead:

* The actor exposes output through ``user_output_config``.
* The actor output decides which data items are active, written to disk, kept in
  memory, or kept per run.
* The data item implements the payload-specific operations: load, merge, write,
  and close.

This makes output merging output-centric rather than actor-centric. A target
actor output receives a source actor output and an output-scoped merge context.
It then decides how to merge the corresponding data. Image output can load one
run, merge it, and clear it. ROOT output delegates streaming to a coordinator.

``DataItem`` instances should behave as enhanced payload objects. For example, a
statistics data item can expose entries from its underlying dictionary-like data
while still providing merge and write operations. ``DataItemContainer`` provides
grouping and item selection, especially for output with several related items
such as dose, squared dose, and uncertainty.


Design goal: keep memory footprint small during merge
-----------------------------------------------------

The merge design should avoid loading every job and every run into memory at
once. This matters for split campaigns with many jobs or large dose images and
ROOT files.

Open-merge-close in image item
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Image data items should support a local workflow:

1. Load only the source image needed for the current contribution.
2. Merge it into the target item.
3. Close or clear the source data.

The merge manager and coordinators should not need to understand image internals.
They provide the context. The actor output and data item implement the
payload-specific open-merge-close sequence.

Chunk-wise streaming of ROOT data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ROOT output needs a different strategy because several actor outputs may write
different trees into the same ROOT file. The ``RootMergeCoordinator`` groups
ROOT merge work by target file and streams child ROOT trees into the merged ROOT
file chunk by chunk.

The streaming merge should:

* Avoid loading the full ROOT file into memory.
* Concatenate child files in split order.
* Remap ``EventID`` when that branch exists.
* Remap ``RunID`` according to the split mapping when that branch exists.
* Preserve branch names and fail on incompatible branch schemas.

ROOT merge metadata is persisted next to ROOT output so a rehydrated simulation
can know which file, tree, and branches were produced. Missing ROOT files can be
legitimate if a configured output received no entries. In that case, metadata
should still record that the output was expected but no ROOT file was written.


What actor code needs to implement so multi job runs work
---------------------------------------------------------

Calls to hooks
^^^^^^^^^^^^^^

Actor code must participate in the standard lifecycle hooks. The important
Python-side hooks are:

``resolve_and_validate_config(context=None)``
    Validate and resolve Python configuration. The ``context`` argument allows
    components to adapt warnings and validation to workflows such as split
    preparation.

``initialize()``
    Initialize runtime state and communicate with C++/Geant4.

``end_simulation_action()``
    Perform Python-side end-of-simulation work that must happen after the C++
    simulation has run, such as actor-output finalization.

``plan_merge()``, ``execute_merge()``, ``finalize_merge()``
    Participate in output merge planning, execution, and final cleanup. In the
    current architecture, actor outputs are the relevant merge units.

For digitizers and other classes with Python/C++ parallel inheritance,
``EndSimulationAction()`` should stay a thin trampoline entry point. Functional
Python code belongs in ``end_simulation_action()`` so derived Python classes can
reuse it safely without accidentally calling the wrong C++ base method.

Digitizers: ROOT
^^^^^^^^^^^^^^^^

Digitizers that write ROOT output need special care:

* ROOT file writing is done during runtime on the C++ side.
* Python actor output metadata must be finalized at the end of the simulation.
* ``keep_data_per_run=True`` for ROOT output means that ``RunID`` must be present
  among the written branches.
* Multiple digitizers may target the same ROOT file through different trees.
  Merge execution must therefore be coordinated by target ROOT file rather than
  by actor alone.

Digitizer implementations should call the shared Python-side finalization helper
so all configured actor outputs get their end-of-simulation callback. If a
digitizer overrides ``EndSimulationAction()``, keep it as a thin forwarder and
put reusable Python logic in ``end_simulation_action()``.

The current ROOT metadata helpers are intentionally pragmatic. Longer term, ROOT
bookkeeping should move out of generic actor base classes and into a dedicated
ROOT controller owned by actors that need ROOT output.

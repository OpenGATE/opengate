Geant4-DNA And Chemistry Architecture
=====================================

This chapter explains how Geant4-DNA electromagnetic track-structure physics
and chemistry are integrated in GATE 10, with a focus on the developer-facing
architecture. It also describes the current pattern for implementing a
chemistry-aware actor.

Scope
-----

In this branch, ``chemistry`` means the Geant4-DNA chemistry workflow:

- a Geant4-DNA track-structure EM configuration is activated in one or more
  regions;
- a Geant4 chemistry list is selected and optionally extended;
- Geant4's chemistry scheduler is configured and started;
- chemistry-aware actors receive dedicated chemistry callbacks;
- chemistry counters are exposed as actor-owned scoring components.

The implementation is deliberately split across:

- python configuration and serialization objects;
- simulation engines that connect the pieces at the right Geant4 lifecycle
  stage;
- C++ bridge classes that forward chemistry callbacks into GATE actors.


High-Level Architecture
-----------------------

The main components are:

- ``PhysicsManager`` / ``PhysicsEngine``:
  configure the Geant4 physics list and region-local track-structure EM
  activation.
- ``ChemistryManager`` / ``ChemistryEngine``:
  resolve the chemistry list request, prepare the active chemistry list,
  configure the Geant4 chemistry scheduler, and configure the shared
  ``G4MoleculeCounterManager`` policy.
- ``ChemistryList``:
  the python-facing chemistry-list object that wraps one built-in Geant4
  chemistry list and optionally appends species, reactions, and dissociation
  channels.
- ``GateVChemistryActor``:
  the C++ base class for chemistry-aware actors.
- ``GateTimeStepAction`` and ``GateITTrackingInteractivity``:
  the Geant4 callback bridges that dispatch chemistry lifecycle events to
  ``GateVChemistryActor`` instances.
- ``ChemistryActorBase``:
  the python base class that adds chemistry-specific actor configuration,
  declarative counters, and chemistry counter outputs.

The design principle is:

- physics and chemistry setup stay in managers and engines;
- simulation-wide chemistry control stays in managers and engines;
- chemistry scoring logic lives in actors;
- detailed chemistry callback forwarding lives in dedicated C++ bridge classes;
- chemistry counters are actor-owned, but their results are exposed through the
  normal actor output system.


Track-Structure EM And Chemistry Activation
-------------------------------------------

Track-structure EM and chemistry are related, but they are not configured by
the same objects.

Track-structure EM
~~~~~~~~~~~~~~~~~~

Region-local Geant4-DNA electromagnetic track-structure physics is configured
through the physics side. In GATE 10 the relevant user-facing name is
``track_structure_em_physics``.

Python objects keep the full Geant4 names, for example:

- ``G4EmDNAPhysics_option2``
- ``G4EmDNAPhysics_option4``
- ``G4EmDNAPhysics_option6``

Only when ``PhysicsEngine`` calls ``G4EmParameters::AddDNA(...)`` are these
translated to the shorter Geant4 region-activator strings.

Chemistry
~~~~~~~~~

Chemistry is enabled through ``ChemistryManager`` and chemistry-aware actors.
The manager and all chemistry actors participate in one uniqueness check for
the chemistry list name. Today the simulation must run with one coherent
chemistry list.

This means:

- the manager may request a chemistry list;
- an actor may also request a chemistry list;
- all such requests must resolve to the same Geant4 list name.

If no chemistry list is requested and the chemistry list has no custom species,
reactions, or dissociations, the chemistry engine remains inactive.


ChemistryList
-------------

``ChemistryManager`` owns a single ``ChemistryList`` instance. This is the
main user-facing and developer-facing chemistry-list object.

It has two responsibilities:

1. represent the selected built-in Geant4 chemistry list;
2. optionally extend it with additional species, reactions, and dissociation
   channels.

Current configurable content includes:

- ``list_name``
- ``chemical_species``
- ``reactions``
- ``dissociations``

Lifecycle
~~~~~~~~~

Before the Geant4 run manager initializes, ``ChemistryEngine`` asks
``ChemistryManager`` whether chemistry is needed. If yes, it calls
``ChemistryList.initialize_before_runmanager()``.

That method:

- resolves the built-in Geant4 chemistry-list class from ``list_name``;
- instantiates that Geant4 list;
- immediately deregisters the built-in instance from
  ``G4DNAChemistryManager``;
- registers the python-facing ``ChemistryList`` itself as the active chemistry
  list.

This is an important design detail: the built-in Geant4 list is used as a
provider of default behavior, while the python-facing ``ChemistryList`` becomes
the single chemistry-list identity known to Geant4.

During the Geant4 physics/chemistry lifecycle, ``ChemistryList`` forwards the
standard chemistry hooks to the built-in list and then applies GATE-side
customizations:

- ``ConstructParticle()`` maps to ``ConstructMolecule()``
- ``ConstructProcess()``
- ``ConstructMolecule()``
- ``ConstructDissociationChannels()``
- ``ConstructReactionTable()``
- ``ConstructTimeStepModel()``

The custom extensions are appended after the built-in list has populated its
default content.

Customization model
~~~~~~~~~~~~~~~~~~~

The current model is additive:

- custom species may define or modify molecule configurations;
- custom reactions are appended to ``G4DNAMolecularReactionTable``;
- custom dissociation channels are added to the corresponding molecule
  definitions.

This keeps the base Geant4 chemistry list as the foundation and lets GATE
extend it rather than replace it wholesale.


Engine Initialization Sequence
------------------------------

The chemistry setup depends on the simulation engine order.

The relevant sequence in ``SimulationEngine.initialize()`` is:

1. initialize geometry;
2. initialize physics before the run manager;
3. initialize sources;
4. prepare chemistry before the run manager;
5. register geometry, physics list, and action engine in Geant4;
6. initialize actors and filters;
7. initialize the Geant4 run manager;
8. finalize physics after the run manager;
9. finalize chemistry after the run manager;
10. link sources and actors and register actor actions.

The chemistry-specific parts are split across the two chemistry engine stages.

Before run-manager initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``ChemistryEngine.initialize_before_runmanager()`` does the following:

- resolves whether chemistry is needed;
- initializes the active ``ChemistryList``;
- attaches that chemistry list to the already-created augmented physics list;
- configures ``G4EmParameters`` with the selected chemistry time-step model;
- resolves and applies the shared ``G4MoleculeCounterManager`` policy required
  by chemistry actors.

After run-manager initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``ChemistryEngine.initialize_after_runmanager()`` installs the runtime callback
bridges used by chemistry-aware actors:

- ``GateTimeStepAction``
- ``GateITTrackingInteractivity``
- optionally one global ``GateChemistryController``

These are attached to ``G4Scheduler``. Chemistry-aware actors are registered as
scorers/observers, while ``GateChemistryController`` is registered only when
``ChemistryManager`` requests simulation-wide chemistry confinement. If no
built-in chemistry list was prepared, this stage is skipped.


Chemistry Callback Bridge
-------------------------

Geant4-DNA chemistry does not use the standard sensitive-detector or primitive
scorer pathway. Instead, the chemistry scheduler exposes dedicated callbacks.

GATE bridges those callbacks through two C++ classes:

- ``GateTimeStepAction``
- ``GateITTrackingInteractivity``

``GateTimeStepAction``
~~~~~~~~~~~~~~~~~~~~~~

This class derives from ``G4UserTimeStepAction`` and dispatches scheduler-level
chemistry events to registered chemistry actors:

- ``StartProcessing()``
- ``NewStage()``
- ``UserPreTimeStepAction()``
- ``UserPostTimeStepAction()``
- ``UserReactionAction()``
- ``EndProcessing()``

In GATE, these map to actor hooks such as:

- ``StartChemistryProcessing``
- ``NewStage``
- ``PreChemistryTimeStepAction``
- ``PostChemistryTimeStepAction``
- ``ChemistryReactionAction``
- ``EndChemistryProcessing``

``GateITTrackingInteractivity``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This class derives from ``G4ITTrackingInteractivity`` and dispatches
chemistry-track-level callbacks:

- ``Initialize()``
- ``AppendStep()``
- ``StartTracking()``
- ``EndTracking()``
- ``Finalize()``

In GATE, these map to actor hooks such as:

- ``InitializeChemistryTracking``
- ``AppendChemistryStep``
- ``StartChemistryTracking``
- ``EndChemistryTracking``
- ``FinalizeChemistryTracking``

``GateVChemistryActor``
~~~~~~~~~~~~~~~~~~~~~~~

All chemistry-aware C++ actors derive from ``GateVChemistryActor``. This class
extends ``GateVActor`` with chemistry-specific virtual hooks.

``GateVChemistryActor`` is now intentionally passive by default. It provides
the callback interface used by:

- chemistry scoring actors such as ``GateChemicalStageActor``;
- dedicated chemistry-control classes such as ``GateChemistryController``.

This design keeps chemistry actors focused on probing and scoring unless they
are explicitly implemented for control purposes.


``GateChemistryController``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``GateChemistryController`` is a dedicated C++ chemistry-control class derived
from ``GateVChemistryActor``.

Its current responsibility is simulation-wide chemistry confinement:

- if ``ChemistryManager.confine_chemistry_to_volume`` is set;
- a single ``GateChemistryController`` is created by ``ChemistryEngine``;
- it is registered into ``GateITTrackingInteractivity``;
- chemistry tracks starting outside the configured logical-volume subtree are
  killed before chemistry processing continues.

This moved chemistry confinement out of ordinary chemistry actors and avoids
interference between multiple scoring actors attached to different volumes.


Chemistry Actors In Python
--------------------------

The python-side base class is ``ChemistryActorBase``.

Its responsibilities are:

- participate in chemistry-actor discovery;
- hold actor-level chemistry configuration such as
  ``chemistry_list_name``;
- own declarative chemistry counters;
- generate one actor output per configured counter;
- collect counter results at the end of the simulation.

Counters are no longer dynamically added user components. Instead, they are
declared by the actor developer through a class-level ``counter_config``. This
matches the normal GATE pattern where an actor declares the scoring quantities
it supports.

At runtime:

- configured counters are instantiated automatically;
- they are attached as ``actor.counters.<counter_name>`` through a ``Box``;
- each counter is associated with one fixed actor output.


Chemistry Counter Architecture
------------------------------

Current chemistry counters are wrappers around built-in Geant4 counters:

- ``BuiltinMoleculeCounter``
- ``BuiltinReactionCounter``

They inherit from:

- a pure-python base class hierarchy
  (``CounterBase``, ``MoleculeCounterBase``, ``ReactionCounterBase``);
- and the corresponding pybind-exposed Geant4 class.

This means the concrete python counter object is itself the Geant4 counter
object. No extra wrapper-by-composition layer is used.

Why actor-owned counters?
~~~~~~~~~~~~~~~~~~~~~~~~~

Counters are treated as part of actor scoring logic:

- the actor developer decides which counters exist;
- the actor decides the shared ``G4MoleculeCounterManager`` policy it needs;
- the actor output system owns the public result surface.

This is important because Geant4-DNA implements counter reset and accumulation
policy on the shared ``G4MoleculeCounterManager``, not independently per
counter.

Results API
~~~~~~~~~~~

Counters expose an internal ``_collect_results()`` method. This is
intentionally internal:

- counters are publicly configurable through ``actor.counters``;
- final results are meant to be accessed through actor outputs.

The in-memory representation returned by ``_collect_results()`` is:

- ``dict[label] -> structured numpy array``

with one structured array per molecule or reaction and two fields:

- ``time``
- ``count``

This is represented in the actor output layer through:

- ``TimeCountSeriesDataItem``
- ``SingleTimeCountSeries``
- ``ActorOutputChemicalCounter``

One chemistry counter corresponds to one actor output.


How To Implement A Chemistry Actor
----------------------------------

The current reference implementation is ``ChemicalStageActor``. A new chemistry
actor should follow the same split between python and C++.

Step 1: Define the python actor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inherit in this order:

- first from ``ChemistryActorBase``
- then from the bound C++ class

Example pattern::

   class MyChemistryActor(ChemistryActorBase, g4.GateMyChemistryActor):

As for all actors in GATE:

- implement ``__initcpp__()``
- implement ``initialize()``
- do not call the C++ constructor in ``__init__()``
- do not use python ``super()`` across the mixed python/C++ boundary

Step 2: Declare counters and outputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the actor needs chemistry counters, declare them through
``counter_config``. For each counter, define:

- ``counter_class``
- ``output_name``
- optional ``counter_kwargs``

The actor may still define additional non-counter outputs through
``user_output_config``.

The actor developer, not the user, decides these output names. Users can then
activate or deactivate them through the normal actor output interface.

Step 3: Define actor-level counter-manager policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the actor relies on molecule or reaction counters, define its required
``G4MoleculeCounterManager`` policy in ``__init__()`` through
``required_molecule_counter_manager_policy``.

This policy belongs to the actor, not to the individual counters, because
Geant4-DNA applies it globally through the shared manager.

Typical flags include:

- ``reset_counters_before_event``
- ``reset_counters_before_run``
- ``reset_master_counter_with_workers``
- ``accumulate_counter_into_master``

Step 4: Add the C++ action names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ``__initcpp__()``, construct the bound C++ actor and register only the
hooks that the actor actually implements using ``AddActions({...})``.

This is how the callback bridge knows which chemistry callbacks should be
dispatched to the actor.

Examples of chemistry-specific action names are:

- ``InitializeChemistryTracking``
- ``AppendChemistryStep``
- ``StartChemistryTracking``
- ``EndChemistryTracking``
- ``FinalizeChemistryTracking``
- ``StartChemistryProcessing``
- ``PreChemistryTimeStepAction``
- ``PostChemistryTimeStepAction``
- ``ChemistryReactionAction``
- ``EndChemistryProcessing``

Standard actor callbacks such as ``BeginOfEventAction`` and
``EndSimulationAction`` still work as usual and can be mixed with the chemistry
ones.

Step 5: Initialize in the correct order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ``initialize()``, the usual pattern is:

1. call ``ChemistryActorBase.initialize(self)``
2. call ``InitializeUserInfo(self.user_info)``
3. bridge any IDs or handles needed by the C++ side
4. call ``InitializeCpp()``

``ChemistryActorBase.initialize()`` is what initializes active counters and
attaches them to the actor at runtime.

Step 6: Implement the C++ actor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Derive the C++ side from ``GateVChemistryActor``.

Typical tasks on the C++ side are:

- parse actor-specific user info in ``InitializeUserInfo()``
- implement only the chemistry hooks you actually need
- keep chemistry scoring logic local to the actor

If the actor needs a built-in molecule counter or reaction counter, let the
python side own and register the counter. The C++ actor should only receive the
minimal runtime information it needs, for example a counter ID.

The current ``ChemicalStageActor`` follows exactly this pattern for the
molecule counter used by its built-in species sampling path.

Step 7: Store results through actor outputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Detailed counter results should not be exposed directly from the counter
objects. Instead:

- counters gather raw data internally;
- the actor stores that data into its dedicated actor outputs;
- users then access the final data through the normal output API.

This keeps chemistry counters as internal scoring backends and preserves the
normal GATE actor-output architecture.


``ChemicalStageActor`` As Reference Implementation
--------------------------------------------------

``ChemicalStageActor`` illustrates the current intended architecture:

- it is a chemistry-aware actor built from ``ChemistryActorBase`` and
  ``GateChemicalStageActor``;
- it declares one built-in molecule counter and one built-in reaction counter;
- it keeps a regular summary output called ``results``;
- detailed molecule and reaction histories are exposed on dedicated outputs:
  ``molecule_counter`` and ``reaction_counter``;
- its C++ side implements chemistry scheduler callbacks and chemistry-track
  callbacks through ``GateVChemistryActor``.

One useful design detail is that the detailed reaction output no longer comes
from a hand-crafted GATE-side reaction histogram. Instead, it uses the built-in
Geant4 reaction counter, which is closer to the underlying chemistry model.


Current Constraints
-------------------

The current implementation has a few intentional limits:

- one simulation must resolve to one coherent chemistry list;
- chemistry counter writing is not implemented yet on the python side;
- chemistry counter merging is currently a simple successive-run merge that
  preserves cumulative counts but does not yet reorder seam-time overlaps;
- ``ChemicalStageActor`` currently assumes at most one molecule counter for its
  built-in C++ species-sampling path.

These are not accidental limitations. They reflect the current stage of the
architecture and should be kept in mind when extending it.


Practical Advice For Further Development
----------------------------------------

When you extend the chemistry stack, try to keep the current split intact:

- put simulation-wide decisions in managers and engines;
- put chemistry-control behavior that alters track fate in dedicated global
  controller objects;
- keep chemistry-list composition in ``ChemistryList``;
- keep chemistry callback forwarding in the dedicated C++ bridge classes;
- keep actor-specific chemistry scoring logic in actors;
- keep detailed counter data behind actor outputs, not as ad hoc side channels.

Following that split has made the current branch much easier to reason about,
especially for initialization order, Geant4 lifecycle interactions, and result
serialization.

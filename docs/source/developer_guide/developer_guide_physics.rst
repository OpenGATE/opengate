Physics
=======

This chapter documents implementation details of GATE's physics handling for
developers. It focuses on the Python-side orchestration around Geant4 physics
objects, i.e. the code that turns user-facing settings into Geant4 regions,
physics constructors, processes, and cuts.

Step Limiter
------------

The step limiter is implemented through Geant4 user limits. On the GATE side,
the relevant code is split across three places:

* ``opengate.managers.PhysicsManager`` exposes the user-facing API.
* ``opengate.physics.Region`` stores per-region user limits and builds the
  corresponding Geant4 region objects.
* ``opengate.physics.UserLimitsPhysics`` is a Geant4 physics constructor that
  adds the required Geant4 processes to the selected particles.

User-facing entry points
~~~~~~~~~~~~~~~~~~~~~~~~

Users set the maximum step size either through the physics manager:

.. code-block:: python

    sim.physics_manager.set_max_step_size(volume.name, 1 * gate.g4_units.mm)

or through the volume convenience method:

.. code-block:: python

    volume.set_max_step_size(1 * gate.g4_units.mm)

Internally, both paths associate the volume with a ``Region`` object and store
the value in ``region.user_limits["max_step_size"]``. If no region exists yet
for the volume, ``PhysicsManager.find_or_create_region()`` creates one. The
world volume is associated with Geant4's ``DefaultRegionForTheWorld``; other
volumes use a GATE-created region named ``<volume_name>_region`` by default.

The particles to which user limits are applied are selected with:

.. code-block:: python

    sim.physics_manager.user_limits_particles = ["proton", "GenericIon"]

This setting is a list-like user input. A single string is accepted by the
setter hook and converted to a one-element list. The special values are:

* ``"all"``: apply user limits to all Geant4 particles known to the particle
  table.
* ``"all_charged"``: add the step limiter to charged particles, following
  Geant4's ``G4StepLimiterPhysics`` behaviour.

Particle names are intentionally not limited to the production-cut aliases
(``gamma``, ``electron``, ``positron``, ``proton``). Any Geant4 particle name is
accepted, after applying the small GATE-to-Geant4 alias translation implemented
by ``translate_particle_name_gate_to_geant4()``.

Region initialization
~~~~~~~~~~~~~~~~~~~~~

During simulation initialization, every ``Region`` runs
``Region.initialize_g4_user_limits()``. If none of the user-limit fields is set,
no ``G4UserLimits`` object is created. Otherwise, GATE creates one and fills all
limits:

* ``max_step_size`` maps to ``G4UserLimits.SetMaxAllowedStep()``.
* ``max_track_length`` maps to ``SetUserMaxTrackLength()``.
* ``max_time`` maps to ``SetUserMaxTime()``.
* ``min_ekine`` maps to ``SetUserMinEkine()``.
* ``min_range`` maps to ``SetUserMinRange()``.

Unset upper limits are replaced by ``FLOAT_MAX`` and unset lower limits by
``0``. This lets one ``G4UserLimits`` object represent only the limits that the
user actually requested.

After that, ``Region.initialize_g4_region()`` creates or finds the Geant4
``G4Region``, attaches the ``G4UserLimits`` object to it, and adds the root
logical volumes associated with the GATE region. This is the part that tells
Geant4 where the user-limit values apply.

Registering the Geant4 processes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``G4UserLimits`` object alone is not sufficient. Geant4 also needs tracking
processes attached to particles so that the limits are actually enforced.

The physics engine checks all regions in
``PhysicsEngine.initialize_user_limits_physics()``:

.. code-block:: python

    if region.need_step_limiter():
        need_step_limiter = True
    if region.need_user_special_cut():
        need_user_special_cut = True

If at least one region needs a maximum step size or another user special cut,
GATE registers ``UserLimitsPhysics`` on the active Geant4 physics list.

``UserLimitsPhysics.ConstructProcess()`` then iterates over the full Geant4
particle table and decides, particle by particle, whether to add:

* ``G4StepLimiter("StepLimiter")`` for ``max_step_size``.
* ``G4UserSpecialCuts("UserSpecialCut")`` for the other user limits.

For explicit particle names and for ``"all"``, GATE adds both processes. For
``"all_charged"``, GATE only adds ``G4StepLimiter`` to charged particles. This
mirrors Geant4's default step-limiter constructor behaviour and avoids applying
the other special cuts unless the user explicitly asked for the particle.

The created Geant4 process objects are stored in
``UserLimitsPhysics.g4_step_limiter_storage`` and
``UserLimitsPhysics.g4_special_user_cuts_storage``. This storage is important:
the objects are created from Python via pybind11, and keeping references avoids
their garbage collection after ``ConstructProcess()`` returns.

Validation and name translation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before processes are added, ``UserLimitsPhysics`` validates all explicitly named
particles against ``G4ParticleTable``. Unknown particles are rejected with a
fatal error. The special selectors ``"all"`` and ``"all_charged"`` are removed
before validation.

The translation helper ``translate_particle_name_gate_to_geant4()`` maps the
historical GATE names used for production cuts to Geant4 names:

* ``electron`` -> ``e-``
* ``positron`` -> ``e+``
* ``gamma`` -> ``gamma``
* ``proton`` -> ``proton``

Names not present in this alias table are passed through unchanged. This is what
allows inputs such as ``"GenericIon"`` or other Geant4 particle names to work
without extending the production-cut particle list.

Important distinction from production cuts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Production cuts and user limits have different particle-name scopes in GATE.
Production cuts are still constrained to the particle aliases in
``cut_particle_names`` because that mirrors Geant4 production-cut usage in GATE.
User limits, including the step limiter, are more general: Geant4 can apply them
to any particle with a process manager.

This distinction is why ``sim.physics_manager.user_limits_particles = "all"``
means all Geant4 particles for user limits. Tests that need the historical
GATE behaviour should explicitly request:

.. code-block:: python

    sim.physics_manager.user_limits_particles = [
        "proton",
        "gamma",
        "electron",
        "positron",
    ]


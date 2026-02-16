.. _filters-label:

Details: Filters
****************

Overview
--------

Filters are objects attached to **Actors** that accept or reject a particle, track, or step based on specific criteria. If a filter rejects a step, the actor will ignore it (e.g., a ``PhaseSpaceActor`` will not record the particle, or a ``KillActor`` will not kill it).

Gate provides a "Pythonic" syntax to create and combine filters naturally using logical operators.

.. code-block:: python

   from opengate.actors.filters import GateFilter

   # 1. Initialize the filter factory (need to provide the sim object)
   F = gate.GateFilter(sim)

   # 2. Create a complex filter logic
   # Example: Keep only gammas with Energy > 100 keV AND (Time < 10 ns OR Unscattered)
   my_filter = (F.ParticleName == "gamma") & (F.KineticEnergy > 100 * keV) & \
               ((F.GlobalTime < 10 * ns) | F.Unscattered)

   # 3. Attach to an actor
   actor.filter = my_filter

Syntax and Logic
----------------

The ``GateFilter`` factory (usually named ``F``) allows you to access simulation attributes directly.

Attribute Comparison
~~~~~~~~~~~~~~~~~~~~

You can compare attributes (like Energy, Time, Position) using standard Python comparison operators: ``<``, ``<=``, ``>``, ``>=``, ``==``, ``!=``.

.. code-block:: python

   # Energy filter
   f1 = F.KineticEnergy > 10 * MeV

   # Position filter (X coordinate)
   f2 = F.PostPosition_X < 0 * mm

   # String/Particle filter
   f3 = F.ParticleName == "proton"

   # String "contains" filter (e.g., matches "proton", "anti_proton")
   f4 = F.ParticleName.contains("proton")

Logical Combination
~~~~~~~~~~~~~~~~~~~

Filters can be combined using bitwise operators:

* **AND** (``&``): Both conditions must be true.
* **OR** (``|``): At least one condition must be true.
* **NOT** (``~``): Invert the condition.

.. warning::
   **Parentheses are mandatory!**
   Due to Python's operator precedence, you must wrap every comparison in parentheses when combining them.

   * **Correct:** ``(F.KineticEnergy > 10) & (F.ParticleName == "gamma")``
   * **Wrong:** ``F.KineticEnergy > 10 & F.ParticleName == "gamma"`` (Raises a syntax error)

Available Attributes
~~~~~~~~~~~~~~~~~~~~

You can filter on any attribute available in the ``GateDigiAttributeManager``. Common attributes include:

* ``KineticEnergy``, ``TotalEnergyDeposit``
* ``GlobalTime``, ``LocalTime``
* ``PostPosition_X``, ``PostPosition_Y``, ``PostPosition_Z``
* ``PreDirection_X``, ``PreDirection_Y``, ``PreDirection_Z``
* ``ParticleName``, ``CreatorProcess``
* ``TrackID``, ``ParentID``, ``RunID``, ``EventID``

Special Filters
---------------

Unscattered Primary Filter
~~~~~~~~~~~~~~~~~~~~~~~~~~

This filter accepts particles that are primary particles and have not yet undergone any interaction (scattering).

.. code-block:: python

   # Syntax 1: Using the property directly
   f = F.UnscatteredPrimaryFlag

   # Syntax 2: Explicit comparison
   f = (F.UnscatteredPrimaryFlag == True)

   # Syntax 3: Reject unscattered (keep only scattered)
   f = ~F.UnscatteredPrimaryFlag

Reference
---------

.. autoclass:: opengate.actors.filters.GateFilter
.. autoclass:: opengate.actors.filters.FilterBase
.. autoclass:: opengate.actors.filters.AttributeComparisonFilter
.. autoclass:: opengate.actors.filters.BooleanFilter
.. autoclass:: opengate.actors.filters.UnscatteredPrimaryFilter
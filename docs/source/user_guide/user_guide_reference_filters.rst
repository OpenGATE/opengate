.. _filters-label:

Details: Filters
****************

Overview
--------

Filters are objects attached to **Actors** that accept or reject a particle, track, or step based on specific criteria. If a filter rejects a step, the actor will ignore it (e.g., a ``PhaseSpaceActor`` will not record the particle, or a ``KillActor`` will not kill it).

Gate provides a "Pythonic" syntax to create and combine filters naturally using logical operators.

.. code-block:: python

   from opengate.actors.filters import GateFilterBuilder

   # 1. Initialize the filter factory
   F = GateFilterBuilder()

   # 2. Create a complex filter logic
   # Example: Keep only gammas with Energy > 100 keV AND (Time < 10 ns OR Unscattered)
   my_filter = (F.ParticleName == "gamma") & (F.KineticEnergy > 100 * keV) & \
               ((F.GlobalTime < 10 * ns) | F.Unscattered)

   # 3. Attach to an actor
   actor.filter = my_filter

You can attach the same filter to multiple actors.

Syntax and Logic
----------------

The ``GateFilterBuilder`` factory (conveniently abbreviated as ``F`` in a user script) allows you to build filters based on simulation attributes.

Attribute Comparison
~~~~~~~~~~~~~~~~~~~~

You can compare attributes (like Energy, Time, Position) using standard Python comparison operators: ``<``, ``<=``, ``>``, ``>=``, ``==``, ``!=``. The results of the comparison statement is the actual filter to be attached to the actor.

.. code-block:: python

   # Energy filter
   f1 = F.KineticEnergy > 10 * MeV

   # Deposited energy filter (e.g. do not store the steps without deposit)
   f2 = F.TotalEnergyDeposit > 0

   # Integer filter (primary particles only)
   f3 = F.TrackID == 1

   # String/Particle filter
   f4 = F.ParticleName == "proton"

   # String "contains" filter (e.g., matches "proton", "anti_proton")
   f5 = F.ParticleName.contains("proton")

The comparison follows the type of the attribute: ``F.TotalEnergyDeposit > 0``
and ``F.TotalEnergyDeposit > 0.0`` are the same filter. Only double, integer
and string attributes can be used; vector attributes (e.g. ``PostPosition``)
cannot.

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

You can filter on any attribute available in the ``GateDigiAttributeManager`` (C++ class). Common attributes include:

* ``KineticEnergy``, ``PreKineticEnergy``, ``TotalEnergyDeposit`` (double)
* ``GlobalTime``, ``LocalTime`` (double)
* ``ParticleName``, ``TrackCreatorProcess``, ``ProcessDefinedStep``, ``TrackVolumeName`` (string)
* ``TrackID``, ``ParentID``, ``RunID``, ``EventID``, ``PDGCode`` (integer)

Vector attributes, such as positions and directions, cannot be used in a filter.

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

.. autoclass:: opengate.actors.filters.GateFilterBuilder
.. autoclass:: opengate.actors.filters.FilterBase
.. autoclass:: opengate.actors.filters.AttributeComparisonFilter
.. autoclass:: opengate.actors.filters.BooleanFilter
.. autoclass:: opengate.actors.filters.UnscatteredPrimaryFilter

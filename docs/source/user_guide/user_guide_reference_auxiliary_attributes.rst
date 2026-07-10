.. _auxiliary-attributes-reference-label:

Reference: Auxiliary Attributes
*******************************


Overview
--------

Auxiliary attributes are simulation-level runtime attributes that expose values
which may be consumed by ROOT-backed actors such as the
:class:`~.opengate.actors.digitizers.PhaseSpaceActor`, by generic filters, and
by other actors internally.

Some auxiliary attributes are stateful and accumulate or propagate information
along a track. Others are getter-only attributes that compute their value
directly from the current Geant4 step.

In all cases, the user workflow is the same:

1. activate the auxiliary attribute in the simulation
2. configure its parameters
3. use its name in an actor attribute list and/or a filter

Example:

.. code-block:: python

   aux = sim.activate_auxiliary_attribute(
       "InteractionCounterAttribute",
       "InteractionCount__compt",
   )
   aux.process_name = "compt"

   phsp = sim.add_actor("PhaseSpaceActor", "phsp")
   phsp.attributes = ["KineticEnergy", aux.name]

   F = gate.GateFilterBuilder()
   phsp.filter = F(aux.name) > 0


InteractionCounterAttribute
---------------------------

Description
~~~~~~~~~~~

Counts how often the current track has undergone a configured Geant4 process.

The user must provide:

- ``process_name``: name of the Geant4 process to count

Optional:

- ``propagate_from_parent_track``: if ``True``, secondaries inherit the
  current counter snapshot from their parent at creation time

Example:

.. code-block:: python

   aux = sim.activate_auxiliary_attribute(
       "InteractionCounterAttribute",
       "InteractionCount__compt",
   )
   aux.process_name = "compt"

Reference
~~~~~~~~~

.. autoclass:: opengate.auxiliary_attributes.InteractionCounterAttribute

.. note::
    The ``ProcessDefinedStepInVolumeAttribute`` "hidden actor" was recently (May 2026) replaced by the ``auxiliary`` actor.
    These docs will get corresponding updates soon.

ProcessDefinedStepInVolumeAttributeLegacy
-----------------------------------------

Description
~~~~~~~~~~~

Counts how often a configured process defined a step in a configured volume
hierarchy for the current track.

The user must provide:

- ``process_name``
- ``volume_name``

Optional:

- ``propagate_from_parent_track``

This attribute is the auxiliary-attribute replacement for the old
actor-based ``ProcessDefinedStepInVolumeAttributeLegacy`` helper.

Example:

.. code-block:: python

   aux = sim.activate_auxiliary_attribute(
       "ProcessDefinedStepInVolumeAttribute",
       "ProcessDefinedStep__compt__water_box",
   )
   aux.process_name = "compt"
   aux.volume_name = "water_box"

..
    Reference
    ~~~~~~~~~

..
    .. autoclass:: opengate.auxiliary_attributes.ProcessDefinedStepInVolumeAttributeLegacy


LastProcessDefinedStepInVolumeAttribute
---------------------------------------

Description
~~~~~~~~~~~

Stores the last non-transportation process that defined a step in the
configured volume hierarchy for the current track.

The user must provide:

- ``volume_name``

Optional:

- ``propagate_from_parent_track``

Example:

.. code-block:: python

   aux = sim.activate_auxiliary_attribute(
       "LastProcessDefinedStepInVolumeAttribute",
       "LastProcess__water_box",
   )
   aux.volume_name = "water_box"

Reference
~~~~~~~~~

.. autoclass:: opengate.auxiliary_attributes.LastProcessDefinedStepInVolumeAttribute


LastInteractionPositionInVolumeAttribute
----------------------------------------

Description
~~~~~~~~~~~

Stores the last interaction position seen on the current track inside the
configured volume hierarchy. The stored position is taken from the pre-step
point of a step whose defining process is not ``Transportation``. If no
qualifying interaction has been seen yet, the attribute returns
``(NaN, NaN, NaN)``.

The user must provide:

- ``volume_name``

Optional:

- ``propagate_from_parent_track``

Example:

.. code-block:: python

   aux = sim.activate_auxiliary_attribute(
       "LastInteractionPositionInVolumeAttribute",
       "LastInteractionPosition__water_box",
   )
   aux.volume_name = "water_box"

Reference
~~~~~~~~~

.. autoclass:: opengate.auxiliary_attributes.LastInteractionPositionInVolumeAttribute


UnscatteredPrimaryAttribute
---------------------------

Description
~~~~~~~~~~~

Exposes a flag indicating whether the current step belongs to an unscattered
primary particle.

Returned values:

- ``1``: unscattered primary
- ``0``: otherwise

This attribute is getter-only and does not use persistent track storage.

Example:

.. code-block:: python

   aux = sim.activate_auxiliary_attribute(
       "UnscatteredPrimaryAttribute",
       "UnscatteredPrimaryAuxFlag",
   )

   F = gate.GateFilterBuilder()
   actor.filter = F(aux.name) == 1

Reference
~~~~~~~~~

.. autoclass:: opengate.auxiliary_attributes.UnscatteredPrimaryAttribute


ParticleAncestorAttribute
-------------------------

Description
~~~~~~~~~~~

Stores information (such as the vertex kinetic energy or vertex position) of the first ancestor of the current particle that matches a configured particle type (by default, ``gamma``). This information is propagated to all descendant secondaries.

Optional:

- ``value_to_store``: The quantity to store for the matched ancestor. Supported values are:

  - ``VertexKineticEnergy`` (default)
  - ``VertexPosition``

- ``particle_name``: The particle type to search for (default: ``"gamma"``).

Example:

.. code-block:: python

   # Store the vertex position of the first gamma ancestor
   att1 = sim.activate_auxiliary_attribute(
       "ParticleAncestorAttribute", "GammaPosition"
   )
   att1.value_to_store = "VertexPosition"
   att1.particle_name = "gamma"

   # Store the vertex kinetic energy of the first gamma ancestor
   att2 = sim.activate_auxiliary_attribute(
       "ParticleAncestorAttribute", "GammaVertexKineticEnergy"
   )
   att2.value_to_store = "VertexKineticEnergy"

Reference
~~~~~~~~~

.. autoclass:: opengate.auxiliary_attributes.ParticleAncestorAttribute


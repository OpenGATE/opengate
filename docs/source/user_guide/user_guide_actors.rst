How to: Actors and Filters
==========================

Introduction
------------

The "Actors" are scorers that can store information during simulation, such as dose map or phase-space (like a "tally" in MCNPX). They can also be used to modify the behavior of a simulation without actually scoring any quantity. For example, the `KillActor`  removes particles ad-hoc from tracking when they reach some defined regions. This is why GATE uses the term "actors" rather than "scorers".

In analogy to other components, an actor can be added to a simulation via the command ``add_actor()``. Example:

.. code-block:: python

  import opengate as gate
  sim = gate.Simulation()
  dose_actor_patient = sim.add_actor("DoseActor", name="dose_actor_patient")

This creates a dose actor, adds it to the internal registry of actors of the simulation  ``sim`` under the name ''dose_actor_patient'' dose and returns a python object that we chose to call ``dose_actor_patient``. Note: The name passed as argument to the function ``add_actor()`` dose not need to match the variable name of the returned actor object, but it makes the script clearer.

The actor can be configured via the object ``dose_actor_patient``.

Attach the actor to a volume
----------------------------

For example, many actors need to be attached to a certain volume in the simulation geometry because the actions of the actor are triggered when a particle enters, exits, or moved inside the volume, depending on the actor.

In the example above, you might want to attach the dose actor to an :class:`~.opengate.geometry.volumes.ImageVolume` containing the patient anatomy via a CT image. You can achievs this with the parameter ``attached_to``. Continuing the above example:

.. code-block:: python

  patient = sim.add_volume("ImageVolume", name="patient")
  dose_actor_patient.attached_to = patient


Actor output
------------

Many actors generate at least one kind of output. Some of them generate multiple  outputs. The :class:`~.opengate.actors.doseactors.DoseActor`, for example, can score deposited energy (:attr:`~.opengate.actors.doseactors.DoseActor.edep`), dose (:attr:`~.opengate.actors.doseactors.DoseActor.dose`), the uncertainty of the deposited energy (:attr:`~.opengate.actors.doseactors.DoseActor.edep_uncertainty`) and of the dose (:attr:`~.opengate.actors.doseactors.DoseActor.dose_uncertainty`), the number of deposits per voxels, (:attr:`~.opengate.actors.doseactors.DoseActor.counts`), and it can provide the density map on the same grid as used for scoring (:attr:`~.opengate.actors.doseactors.DoseActor.density`).

Other actors, as many digitizers and the :class:`~.opengate.actors.digitizers.PhaseSpaceActor`, only provide a single ROOT output, e.g. (:attr:`~.opengate.actors.digitizers.PhaseSpaceActor.root_output`).



The list of actors is here: :ref:`actors-label`.
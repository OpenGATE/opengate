How to: Actors and Filters
==========================

.. note:: This section is a general guide on how to use actors in GATE. A detailed description of all actors is here: :ref:`actors-label`.

Introduction
------------

The "Actors" are scorers that can store information during simulation, such as dose map or phase-space (like a "tally" in MCNPX). They can also be used to modify the behavior of a simulation without actually scoring any quantity. For example, the :class:`~.opengate.actors.miscactors.KillActor`  removes particles ad-hoc from tracking when they reach some defined regions. This is why GATE uses the term "actors" rather than "scorers".

In analogy to other components, an actor can be added to a simulation via the command :meth:`~.opengate.managers.ActorManager.add_actor`. Example:

.. code-block:: python

  import opengate as gate
  sim = gate.Simulation()
  dose_actor_patient = sim.add_actor("DoseActor", name="dose_actor_patient")

This creates a dose actor, adds it to the internal registry of actors of the simulation  ``sim`` under the name ''dose_actor_patient'' dose and returns a python object that we chose to call ``dose_actor_patient``. Note: The name passed as argument to the function ``add_actor()`` dose not need to match the variable name of the returned actor object, but it makes the script clearer.
The actor in this example can be configured via the object ``dose_actor_patient``.

Attach the actor to a volume
----------------------------

Many actors need to be attached to a certain volume in the simulation geometry because the actions of the actor are triggered when a particle enters, exits, or moved inside the volume, depending on the actor.

In the example above, you might want to attach the dose actor to an :class:`~.opengate.geometry.volumes.ImageVolume` containing the patient anatomy via a CT image. You can achieve this with the parameter :attr:`~.opengate.actors.base.ActorBase.attached_to`. Continuing the above example:

.. code-block:: python

  import opengate as gate
  sim = gate.Simulation()
  dose_actor_patient = sim.add_actor("DoseActor", name="dose_actor_patient")
  patient = sim.add_volume("ImageVolume", name="patient")
  dose_actor_patient.attached_to = patient


Actor output
------------

Many actors generate at least one kind of output. Some of them generate multiple outputs. The :class:`~.opengate.actors.doseactors.DoseActor`, for example, can score deposited energy (:attr:`~.opengate.actors.doseactors.DoseActor.edep`), dose (:attr:`~.opengate.actors.doseactors.DoseActor.dose`), the uncertainty of the deposited energy (:attr:`~.opengate.actors.doseactors.DoseActor.edep_uncertainty`) and of the dose (:attr:`~.opengate.actors.doseactors.DoseActor.dose_uncertainty`), the number of deposits per voxels, (:attr:`~.opengate.actors.doseactors.DoseActor.counts`), and it can provide the density map on the same grid as used for scoring (:attr:`~.opengate.actors.doseactors.DoseActor.density`).

Other actors, e.g. many digitizers and the :class:`~.opengate.actors.digitizers.PhaseSpaceActor`, only provide a single ROOT output, e.g. (:attr:`~.opengate.actors.digitizers.PhaseSpaceActor.root_output`).

You can configure the output of an actor in different ways, depending whether the actor has one or multiple outputs.

Configure the output filename
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Actors with a single output
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :class:`~.opengate.actors.digitizers.PhaseSpaceActor` has only a single output, namely a ROOT file.

.. code-block:: python

  import opengate as gate
  sim = gate.Simulation()
  sim.output_dir = "/my/preferred/location/"
  phsp_actor1 = sim.add_actor("PhaseSpaceActor", name="phsp_actor1")
  phsp_actor1.output_filename = 'phsp1.root'
  phsp_actor2 = sim.add_actor("PhaseSpaceActor", name="phsp_actor1")
  phsp_actor2.output_filename = 'phsp2.root'

In the example above, we set the global output directory of the simulation to our preferred location via :attr:`~.opengate.managers.Simulation.output_dir` and define the filename for each actor via :attr:`~.opengate.acrtors.digitizers.PhaseSpaceActor.output_filename`. GATE will automatically combine the filenames with the output path. You can also use relative paths including subfolders, like:

.. code-block:: python

  from pathlib import Path
  subfolder = Path('phsp')
  phsp_actor1.output_filename = subfolder / 'phsp1.root'
  phsp_actor2.output_filename = subfolder / 'phsp2.root'

This will create a subfolder ''phsp'' in your preferred output folder defined via ``sim.output_dir = "/my/preferred/location/"`` and save the ROOT files in there.

.. note:: We highly recommend the pathlib library to work with paths. It makes things very easier and platform independent.

You can also decide not to write data to disk, if you wish so. In the above example, set :attr:`~.opengate.acrtors.digitizers.PhaseSpaceActor.write_to_disk` to ``False``:

.. code-block:: python

  phsp_actor1.write_to_disk = False


Actors with multiple outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your actor handles more than one output, you can configure each output individually. The :class:`~.opengate.actors.doseactors.DoseActor` is a good example. If you want to score deposited energy as well as dose and dose uncertainty, you can do this:

.. code-block:: python

  import opengate as gate
  sim = gate.Simulation()
  sim.output_dir = "/my/preferred/location/"

  dose_actor_patient = sim.add_actor("DoseActor", name="dose_actor_patient")

  dose_actor_patient.dose.active = True
  dose_actor_patient.dose_uncertainty.active = True

This turns on dose and dose_uncertainty, which are inactive by default. Deposited energy scoring, :attr:`~.opengate.actors.doseactors.DoseActor.edep`, is always active.

You can specify the filename individually per output, e.g.

.. code-block:: python

  dose_actor_patient.edep.output_filename = "patient_deposited_energy.mhd"
  dose_actor_patient.dose.output_filename = "patient_dose.mhd"
  dose_actor_patient.dose_uncertainty.output_filename = "patient_dose_uncertainty.mhd"

or, you can set a filename via the actor:

.. code-block:: python

  dose_actor_patient = "dose_actor_patient.mhd"

In this latter case, GATE will automatically append a suffix to each output corresponding to the output name, i.e. ''dose_actor_patient-edep.mhd'', ''dose_actor_patient-dose.mhd'',m and ''dose_actor_patient-dose_uncertainty.mhd''.

Accessing output data via file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The common way of accessing actor output is by opening the file(s) the actor wrote to your disk. To this end, the most convenient way to get the output path is to ask the actor.

In case your actor handles a single output, as for example the :class:`~.opengate.actors.digitizers.PhaseSpaceActor`, you can do:

.. code-block:: python

  # this gives you an absolute path as a pathlib.Path object
  path_to_root_file = phsp_actor1.get_output_path()
  # if you need the string, do
  path_to_root_file_string = str(path_to_root_file)

In case your actor handles multiple outputs, get the path for the output you want. For the :class:`~.opengate.actors.doseactors.DoseActor`, for example:

.. code-block:: python

  path_to_dose = dose_actor_patient.dose.get_output_path()
  path_to_dose_uncertainty = dose_actor_patient.dose_uncertainty.get_output_path()


Accessing output data via directly from memory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The nice thing about GATE 10 is that your simulation actually runs in a python session. So you might might want to do some post-processing right after the end of your simulation. In this case, you can directly access the output data from your actor **without** reading any file from disk.

If your actor supports this, like e.g. the :class:`~.opengate.actors.doseactors.DoseActor`, you can do:

.. code-block:: python

  import numpy as np

  # these are ITK images
  dose_image = dose_actor_patient.dose.image
  dose_uncertainty_image = dose_actor_patient.dose_uncertainty.image

  # you can convert them to numpy arrays, if you want:
  dose_array = np.asarray(dose_image)
  dose_uncertainty_array = np.asarray(dose_uncertainty_image)

In the above example, you will get the dose and dose_uncertainty, respectively, scored over the entire simulation.

The property :attr:`~.opengate.actors.actoroutput.UserInterfaceToActorOutputImage.image` is a shortcut specific to image-like output that is equivalent to

.. code-block:: python

  # these are ITK images
  dose_image = dose_actor_patient.dose.get_data()
  dose_uncertainty_image = dose_actor_patient.dose_uncertainty.get_data()


.. note:: Currently, actors with ROOT output do not support access to the ROOT structure via memory. You have to load the file from disk, e.g. with ``uproot``.


Actor output in simulations with multiple runs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You simulation might have multiple internal runs (G4Runs), e.g. because part of the geometry is dynamic (moving volumes, 4D CT image). In this case, many actors can store the output data per run additionally to the output data corresponding to the entire simulation. To activate that for specific output, use:

.. code-block:: python

  dose_actor_patient.dose.keep_data_per_run = True
  dose_actor_patient.dose_uncertainty.keep_data_per_run = True

Alternatively, you can apply the setting to all outputs of the actor:

.. code-block:: python

  dose_actor_patient.keep_data_per_run = True
  print(dose_actor_patient.dose.keep_data_per_run)
  print(dose_actor_patient.dose_uncertainty.keep_data_per_run)

To access data from a specific run, you need to use the :meth:`~.opengate.actors.actoroutput.BaseUserInterfaceToActorOutput.get_data` method with the keyword argument ``which``:

.. code-block:: python

  # This is the dose image from the second run because indexing starts at 0
  dose_runindex_1 = dose_actor_patient.dose.get_data(which=1)


References
----------


Common parameters and functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: opengate.managers.ActorManager.add_actor

.. automethod:: opengate.managers.ActorManager.remove_actor

.. autoproperty:: opengate.actors.base.ActorBase.attached_to

.. autoproperty:: opengate.actors.base.ActorBase.filters

.. autoproperty:: opengate.actors.base.ActorBase.priority

Actor output
~~~~~~~~~~~~

.. automethod:: opengate.actors.actoroutput.BaseUserInterfaceToActorOutput.get_data

.. automethod:: opengate.actors.actoroutput.BaseUserInterfaceToActorOutput.get_output_path

.. autoproperty:: opengate.actors.actoroutput.BaseUserInterfaceToActorOutput.output_filename

.. autoproperty:: opengate.actors.actoroutput.BaseUserInterfaceToActorOutput.write_to_disk

.. autoproperty:: opengate.actors.actoroutput.BaseUserInterfaceToActorOutput.keep_data_per_run

.. autoproperty:: opengate.actors.actoroutput.BaseUserInterfaceToActorOutput.active


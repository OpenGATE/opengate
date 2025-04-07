Set up a first simulation
=========================

The Simulation object
----------------------

Any simulation starts by defining the :class:`~.opengate.managers.Simulation` object.
A script can only contain **one** such :class:`~.opengate.managers.Simulation` object.

.. code-block:: python

   import opengate as gate
   sim = gate.Simulation()

You can set general options via the :class:`~.opengate.managers.Simulation` object, for example:

.. code-block:: python

   import opengate as gate

   sim = gate.Simulation()
   sim.g4_verbose = False
   sim.visu = False
   sim.random_seed = 'auto'
   sim.number_of_threads = 1

To know all input parameters and their default values, you can do:

.. code-block:: python

   import opengate as gate
   gate.help_on_user_info(gate.Simulation)

To get help about a specific input parameter, you can do:

.. code-block:: python

   import opengate as gate
   gate.help_on_user_info(gate.Simulation.number_of_threads)

Components of a simulation
--------------------------

A simulation usually contains four kinds of main components that will be described in more detail further down:

- **Geometry**: all geometrical elements that compose the scene, such as phantoms, detectors, etc. These are referred to as *Volumes*.
- **Sources**: all sources of primary particles.
- **Physics**: the physics models used by Geant4 and their parameters.
- **Actors**: these are the building blocks that actually extract information from the simulation and generate output, or that interact and steer the simulation. Typical examples are actors that calculate dose deposition on a voxel grid or detect particles and their properties. Note: other Monte Carlo use the term 'scorer'.

The general structure of a GATE 10 simulation script follows this simple example:

.. code-block:: python

   import opengate as gate

   if __name__ == "__main__":
       sim = gate.Simulation()
       sim.output_dir = <YOUR_OUTPUT_DIRECTORY_OF_CHOICE>

       wb = sim.add_volume("Box", name="waterbox")
       # configure the volume ...
       cm = gate.g4_units.cm
       wb.size = [10 * cm, 5 * cm, 10 * cm]
       # ...

       source = sim.add_source("GenericSource", name="Default")
       MeV = gate.g4_units.MeV
       Bq = gate.g4_units.Bq
       source.particle = "proton"
       source.energy.mono = 240 * gate.g4_units.MeV
       # ...

       stats = sim.add_actor("SimulationStatisticsActor", "Stats")

       sim.run()

The simulation is started by the command ``sim.run()``. Optionally, the simulation can be run in a subprocess via

.. code-block:: python

   sim.run(start_new_process=True)

This is necessary if a simulation is run multiple times from the same script, e.g., in a loop, or when working in an interactive python terminal or notebook.

.. important::

   You **should always** place the part of the script that actually executes the simulation in a block protected by ``if __name__ == "__main__":``, as in the example above. Key functionalities of GATE 10 will not work otherwise.


Units
-----

Geant4 physics units are collected in `opengate.g4_units` and you can assign the ones you need to a variable inside your script for convenience:

.. code-block:: python

   import opengate as gate

   cm = gate.g4_units.cm
   eV = gate.g4_units.eV
   MeV = gate.g4_units.MeV
   x = 32 * cm
   energy = 150 * MeV
   print(f'The energy is {energy/eV} eV')

The units behave like in the Geant4 `system of units <https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Fundamentals/unitSystem.html>`_.


References
----------

.. autoclass:: opengate.managers.Simulation

.. automethod:: opengate.managers.Simulation.run

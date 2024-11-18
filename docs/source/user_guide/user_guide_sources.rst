***************
How to: Sources
***************

Sources are the objects that create the primary particles in a simulation.
A GATE simulation can contian multiiple sources at the same time.

Information about the availavble sources may be displayed with:

.. code:: python

   # Print all types of source
   print(sim.dump_source_types())

   # Print information about all sources
   print(sim.dump_sources())

Look at the section :ref:`sources-detailed-label` in the detailed part of the user guide for a description of all available sources and their parameters.


How to add a source
===================

You can add a to the simulation like this:

.. code:: python

    sim = gate.Simulation()
    # ...
    source1 = sim.add_source('Generic', 'MyFirstSource')
    source2 = sim.add_source('Voxels', 'MySecondSource')


How to set the number of primaries
==================================

You will obviously want to specify how many primary particles the source should produce.
The preferred way to do that is by specifying the activity, i.e. how many particles per time interval are produced. Continuing the example above:

.. code-block:: python

    source2.activity = 10 * gate.g4_units.Bq

The total number of particles is given by this activity and the length of the run timing interval(s) of the simulation. **Be default, a GATE simulation has one run timing interval that is 1 second long**. The source ``source2`` above will therefore produce 10 particles on total.

In simulations with multiple run timing intervals, e.g. in moving geometries, the number of primary particles per run is the source activity times the length of each run timing interval.

Alternatively, you can specify the fixed number of primary particles to be generated, e.g.

.. code-block:: python

    source1.n = 100

Note, however, that certain functionality regarding simulations with multiple runs is currently not supported when sources specify the fixed number of particles as above.


How to position the source in space
===================================

Geant4 creates primary particles *ex nihilo*, i.e. out of nothing anywhere in the simulation geometry. It is often convenient, however, to have a source follow a volume, e.g. if the source is actually inside the gantry of a linac in radiotherapy. Therefore, you can attach the source to a volume. For the ``source2`` from above, this would be:

.. code-block:: python

    my_gantry = sim.add_volume("BoxVolume", name="my_gantry")
    source2.attached_to = my_gantry

Whenver the volume ``my_gantry`` moves, the source will move with it.

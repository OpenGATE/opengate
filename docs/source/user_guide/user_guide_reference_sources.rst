.. _sources-detailed-label:

Details: Sources
****************

Common parameters
=================

Sources are the objects that create particles *ex nihilo*. The particles
created from sources are called the *Event* in the Geant4 terminology,
they got a *EventID* which is unique in a given *Run*.

Several sources can be defined and are managed at the same time. To add
a source description to the simulation, you do:

.. code:: python

   source1 = sim.add_source('GenericSource', 'source1')
   source1.n = 100

   source2 = sim.add_source('VoxelSource', 'source2')
   source2.activity = 10 * g4_units.Bq

There are several source types, each one with different parameter. In
this example, ``source1.n`` indicates that this source will generate 100
Events. The second source manages the time and will generate 10 Events
per second, so according to the simulation run timing, a different
number of Events will be generated.

Information about the sources may be displayed with:

.. code:: python

   # Print all types of source
   print(sim.dump_source_types())

   # Print information about all sources
   print(sim.dump_sources())

Some of the parameters are common to **all** types of sources, while others
are specific to a certain type of source.
Given a source ``source``, use ``print(source)`` to display the
source's parameters and their default values.

Common parameters are:

* | ``attached_to``: the name of the volume to which the source is attached (``world`` by default) in the hierarchy of volumes.
  | See :ref:`geometry-and-volumes` for more details.
* | ``position.translation``: list of 2 numerical values, e.g. ``[0, 2 * cm, 3 * mm]``.
  | It defines the translation of the source with respect to the reference frame of the attached volume.
  | Note: the origin of the reference frame is always at the center of the shape in Geant4.
* | ``rotation``: a 3×3 rotation matrix.
  | Rotation of the volume with respect to the attached volume.
  | We advocate the use of `scipy.spatial.transform.Rotation` to manage the rotation matrix.
* | ``n``: the number (integer) of particles to emit (the number of Geant4 Events).
* | ``activity``: the number (real, in Bq) of particle to emit per second.
  | The number of Geant4 Events will depend on the simulation time.


Coordinate system
-----------------

The :attr:`~.opengate.sources.base.SourceBase.attached_to` option indicates the coordinate system of the source. By
default, it is the world, but it is possible to attach a source to any
volume. In that case, the coordinate system of all emitted particles
will follow the given volume.
Using ``source.direction_relative_to_attached_volume = True`` will make
your source direction change following the rotation of that volume.


Reference
---------

.. autoproperty:: opengate.sources.base.SourceBase.attached_to

The current types of sources are the following:

* :ref:`source-generic-source`
* :ref:`source-voxel-source`
* :ref:`source-ion-pencil-beam-source`
* :ref:`source-treatment-plan-pencil-beam-source`
* :ref:`source-gan-source`
* :ref:`source-phid-source`


.. include:: user_guide_reference_sources_generic_source.rst
.. include:: user_guide_reference_sources_voxel_source.rst
.. include:: user_guide_reference_sources_ion_pencil_beam_source.rst
.. include:: user_guide_reference_sources_treatment_plan_pencil_beam_source.rst
.. include:: user_guide_reference_sources_gan_source.rst
.. include:: user_guide_reference_sources_phid_source.rst

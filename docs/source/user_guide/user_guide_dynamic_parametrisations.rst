Dynamic parametrisations
========================

Dynamic parametrisations provide a user-facing way to change parts of a
simulation from one run to the next. They are used for dynamic geometry, such
as moving or rotating volumes, and also for dynamic sources, such as a
``VoxelSource`` whose activity image changes over time.

The key idea is simple:

- a simulation is split into several internal runs,
- each run corresponds to one time interval,
- a dynamic object provides one value per run for each dynamic parameter.


Run timing intervals
--------------------

The temporal structure of a dynamic simulation is defined by
``sim.run_timing_intervals``.

Example:

.. code-block:: python

   sec = gate.g4_units.s

   sim.run_timing_intervals = [
       (0.0 * sec, 0.5 * sec),
       (0.5 * sec, 1.0 * sec),
       (1.5 * sec, 2.0 * sec),
   ]

Each tuple corresponds to one Geant4 run. The intervals do not need to be
continuous: gaps are allowed.

For dynamic parametrisations, the important rule is:

- if there are ``N`` run timing intervals, there must be ``N`` values for each
  dynamic parameter.


General user interface
----------------------

Dynamic objects use the method:

.. code-block:: python

   obj.add_dynamic_parametrisation(...)

The arguments of this method are the dynamic parameters and their values for
each run.

For example, a translation evolving over three runs could be specified as:

.. code-block:: python

   box.add_dynamic_parametrisation(
       translation=[
           [0 * mm, 0 * mm, 0 * mm],
           [5 * mm, 0 * mm, 0 * mm],
           [10 * mm, 0 * mm, 0 * mm],
       ]
   )

The same interface is used for other dynamic parameters, such as rotation or
image.


Dynamic geometry
----------------

Moving a volume
~~~~~~~~~~~~~~~

Volumes can be moved dynamically by providing one translation per run:

.. code-block:: python

   import opengate as gate

   sim = gate.Simulation()
   mm = gate.g4_units.mm
   sec = gate.g4_units.s

   sim.run_timing_intervals = [
       (0.0 * sec, 1.0 * sec),
       (1.0 * sec, 2.0 * sec),
       (2.0 * sec, 3.0 * sec),
   ]

   box = sim.add_volume("Box", "moving_box")
   box.size = [50 * mm, 50 * mm, 50 * mm]
   box.material = "G4_WATER"

   box.add_dynamic_parametrisation(
       translation=[
           [0 * mm, 0 * mm, 0 * mm],
           [10 * mm, 0 * mm, 0 * mm],
           [20 * mm, 0 * mm, 0 * mm],
       ]
   )

Rotating a volume
~~~~~~~~~~~~~~~~~

Rotations follow the same pattern. One rotation matrix is provided per run:

.. code-block:: python

   from scipy.spatial.transform import Rotation

   rot0 = Rotation.from_euler("z", 0, degrees=True).as_matrix()
   rot1 = Rotation.from_euler("z", 20, degrees=True).as_matrix()
   rot2 = Rotation.from_euler("z", 40, degrees=True).as_matrix()

   box.add_dynamic_parametrisation(
       rotation=[rot0, rot1, rot2]
   )

Translation and rotation can also be combined in a single dynamic
parametrisation.


Dynamic image volumes
---------------------

``ImageVolume`` also supports a dynamic ``image`` parameter. This allows, for
example, the use of a 4D CT where the image changes from run to run.

.. code-block:: python

   patient = sim.add_volume("Image", "patient")
   patient.image = "ct_0.mhd"
   patient.material = "G4_AIR"
   patient.voxel_materials = [[0, 10000, "G4_WATER"]]

   patient.add_dynamic_parametrisation(
       image=[
           "ct_0.mhd",
           "ct_1.mhd",
           "ct_2.mhd",
       ]
   )

This uses the same interface as dynamic translations and rotations: one value
per run.


Dynamic voxel source
--------------------

``VoxelSource`` supports a dynamic ``image`` parameter for the activity map.
This means that the source distribution can change from one run to the next
while keeping the same source object.

Example:

.. code-block:: python

   source = sim.add_source("VoxelSource", "vox_source")
   source.attached_to = patient.name
   source.particle = "alpha"
   source.image = "activity_0.mhd"
   source.direction.type = "iso"
   source.energy.mono = 1 * MeV
   source.n = [2000, 2000, 2000]

   source.add_dynamic_parametrisation(
       image=[
           "activity_0.mhd",
           "activity_1.mhd",
           "activity_2.mhd",
       ]
   )

This follows the same user interface as the dynamic image of an
``ImageVolume``.


Aligning activity and CT images
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the activity image and the CT image share the same image coordinate
system, the voxel source should usually be translated so that both image centers
match in the GATE convention.

This can be done with:

.. code-block:: python

   source.position.translation = gate.image.get_translation_between_images_center(
       patient.image, "activity_0.mhd"
   )

See also the voxel source reference page for additional details on image
alignment.


Automatic changers
------------------

In the normal user workflow, no extra setup is needed beyond
``add_dynamic_parametrisation(...)``. For supported dynamic parameters, GATE
creates and configures the required runtime changer automatically.

So for most users, dynamic parametrisations are simply:

1. define ``sim.run_timing_intervals``,
2. call ``add_dynamic_parametrisation(...)``,
3. provide one value per run.

Advanced users can also create custom changers manually, but this is typically
not needed for standard moving-geometry or dynamic-voxel-source use cases.


Per-run output
--------------

When a simulation contains dynamic components, it is often useful to retrieve
actor outputs separately for each run.

Many outputs support this with:

.. code-block:: python

   actor_output.keep_data_per_run = True

This is particularly useful to inspect how a moving geometry or changing source
affects the result from one run to the next.


See also
--------

- :doc:`user_guide_reference_simulation`
- :doc:`user_guide_reference_volumes`
- :doc:`user_guide_reference_sources_voxel_source`

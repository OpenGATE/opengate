How to: Geometry and volumes
============================

Gate fundamentally relies on the geometry principles of Geant4, but
provides the user with an easy-to-use interface to set up the geometry
of a simulation. In this part of the Gate user guide, we explain how a
simulation geometry is set up in Gate.

Under the hood, geometry is handled and parametrized by Geant4. GATE
just sets it up for you. Therefore, it might be worthwhile looking at
the `Geant4 user
guide <http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html#constructed-solid-geometry-csg-solids>`__
as well.

Volumes are the components that make up the simulation geometry.
Following Geant4 logic, a volume contains information about its shape,
its placement in space, its material, and possibly settings about
physics modeling within that volume. In Gate, all these properties are
stored and handled in a single volume object, e.g.a :class:`opengate.geometry.volumes.BoxVolume`,
:class:`opengate.geometry.volumes.SphereVolume`, :class:`opengate.geometry.volumes.ImageVolume`.

Create a volume
---------------

Volumes are managed by the VolumeManager and can be created in two ways:

1) … with the ``add_volume`` command, providing the type of volume as
   string argument. It is mandatory to provide a unique name as well. A
   volume is created according to the specified volume type and the
   volume object is returned. Example:

.. code:: python

   import opengate as gate
   sim = gate.Simulation()
   myboxvol = sim.add_volume('Box', name='mybox')

Most users will opt for this way of creating volumes.

2) … by calling the volume class. In this case, the volume is created,
   but not yet added to the simulation. It has to be added to the
   simulation explicitly. Example:

.. code:: python

   import opengate as gate
   sim = gate.Simulation()
   myspherevol = gate.geometry.volumes.SphereVolume(name='mysphere')
   sim.add_volume(myspherevol)

This second way of creating volumes is useful in cases where the volume
is needed but should not be part of the simulation. For example, if it
serves as basis for a :ref:`boolean operation <boolean_vol>`, e.g. to
be intersected with another volume.

Note that the ``add_volume`` command in the second example does not
require the ``name`` because the volume already exists and already has a
name. For the same reason, the ``add_volume`` command does not return
anything, i.e. it returns ``None``.

Note: Every simulation has a default volume called ``world`` (lowercase)
which is automatically created.

Set the parameters of a volume
------------------------------

The parameters of a volume can be set as follows:

.. code:: python

   import opengate as gate
   sim = gate.Simulation()
   vol = sim.add_volume('Box', 'mybox')
   vol.material = 'G4_AIR'
   vol.mother = 'world'  # by default
   cm = gate.g4_units.cm
   mm = gate.g4_units.mm
   vol.size = [10 * cm, 5 * cm, 15 * mm]

Use ``print`` to get an overview of all the parameters of a volume:

.. code:: python

   print(vol)

In an interactive python console, e.g. ipython, you can also type
``help(vol)`` to get an explanation of the parameters.

To dump a list of all available volume types:

.. code:: python

   print('Volume types :')
   print(sim.volume_manager.dump_volume_types())

Examples of volumes
-------------------

These are examples of how to add and configure volumes in Gate. A more detailed description is in section :ref:`volumes-reference-label`.
A test with all available volumes is available in `test0089_geometries.py <https://github.com/OpenGATE/opengate/blob/master/opengate/tests/src/geometry/test089_geometries.py>`_.

.. code:: python

   # A box
   myBoxVolume = sim.add_volume("Box", "myBoxVolume")
   myBoxVolume.size = [8 * cm, 20 * cm, 8 * cm]
   myBoxVolume.translation = [0 * cm, 8 * cm, 0 * cm]
   myBoxVolume.mother = "world"
   myBoxVolume.material = "Water" # from your GateMaterials.db
   myBoxVolume.color = [0, 0, 0, 0.5]


.. code:: python

   # A sphere
   mySphereVolume = sim.add_volume("Sphere", "mySphereVolume")
   mySphereVolume.mother = "world"
   mySphereVolume.rmin = 0 * cm
   mySphereVolume.rmax = 5 * cm
   mySphereVolume.translation = [0 * cm, 0 * cm, 20 * cm]
   mySphereVolume.material = "Water" # from your GateMaterials.db
   mySphereVolume.color = [1, 0, 0, 1]


Volume hierarchy
----------------

All volumes have a parameter ``mother`` which contains the name of the
volume to which they are attached. You can also pass a volume object to
the ``mother`` parameter and Gate will extract its name from it. By
default, a volume’s mother is the world volume (which has the name
``world``). Gate creates a hierarchy of volumes based on each volume’s
``mother`` parameter, according to Geant4’s logic of hierarchically
nested volumes. The volume hierarchy can be inspected with the function
:meth:`opengate.managers.VolumeManager.dump_volume_tree` of the volume manager. Example:

.. code:: python

   import opengate as gate
   sim = gate.Simulation
   b1 = sim.add_volume('Box', name='b1')
   b1_a = sim.add_volume('Box', name='b1_a')
   b1_b = sim.add_volume('Box', name='b1_b')
   b1_a.mother = b1
   b1_b.mother = b1
   sim.volume_manager.dump_volume_tree()

Take a look at `test007 <https://github.com/OpenGATE/opengate/blob/master/opengate/tests/src/geometry/test007_volumes.py>`_ as example for simple volumes.

Utility properties
------------------

Volume objects come with several properties which allow you to extract
information about the volume. The following description assumes that you
have created a volume already, i.e.

.. code:: python

   import opengate as gate
   sim = gate.Simulation()
   mysphere = sim.add_volume('SphereVolume', name='mysphere')

You can use the following properties to obtain information about the
volume ``mysphere``: - ``mysphere.volume_depth_in_tree``: this yields
the depth in the hierarchy tree of volumes where *0* is the world, *1*
is a volume attached to the world, *2* the first-level subvolume of
another volume, and so forth. - ``mysphere.world_volume``: returns the
world volume to which this volume is linked through the volume
hierarchy. Useful in a simulation with `parallel
worlds <#parallel-worlds>`__. - ``mysphere.volume_type``: returns the
volume type, e.g. “BoxVolume”, “BooleanVolume”, “ImageVolume”.
Technically speaking, it yields the name of the volume’s class. -
``mysphere.bounding_limits``: returns the corner coordinates (3 element
list: (x,y,z)) of the bounding box of the volume -
``mysphere.bounding_box_size``: returns the size of the bounding box
along x, y, z

Note that the above properties are read-only - you cannot set their
values.

.. _materials_section:

Materials
---------

From the simulation point of view, a material is a set of parameters
describing its chemical composition and physical properties such as its
density.

Geant4 defines a set of default materials which are also available in
GATE. A prominent example is “G4_WATER”. The full list of Geant4
materials is available
`here <https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Appendix/materialNames.html>`__.

On top of that, Gate provides different mechanisms to define additional
materials. One option is via a text file which can be loaded with

.. code:: python

   sim.volume_manager.add_material_database("GateMaterials.db")

All material names defined in the “GateMaterials.db” can then be used
for any volume. Please check the file in ``tests/data/GateMaterials.db``
for the required format of database file.

A material can also be described using isotopes. An example is available
in ``tests/data/GateMaterials_Isotopes.db``. The format is similar to the
one used for elements, but with the addition of a line starting with
``[Isotopes]``.

.. raw:: html

   <!--
   Alternatively, materials can be created within a simulation script with the following command:

   ```python
   import opengate
   gate.volume_manager.new_material("mylar", 1.38 * gcm3, ["H", "C", "O"], [0.04196, 0.625016, 0.333024])
   ```

   This function creates a material named "mylar", with the given mass density and the composition (H C and O here) described as a vector of percentages. Note that the weights are normalized. The created material can then be used for any volume.
   -->

Parallel worlds
---------------

In Geant4, volumes must not overlap; any intersection between volumes can lead to undefined behavior since Geant4 cannot reliably determine which volume a particle belongs to. However, certain scenarios, such as those encountered in SPECT simulations with body-contour trajectories, require describing volumes that intersect. For example, simulating a patient represented by a voxelized CT image might result in an overlap with detector components. Such overlaps could produce inaccurate simulations due to ambiguity in volume assignments.

The concept of “parallel worlds” in Geant4 addresses this issue by allowing overlapping volumes to exist in separate, independent worlds. Each “world” operates without interference from the others, enabling accurate simulation while maintaining the required geometric relationships. When a particle is tracked in both volumes at the same time, the second world is chosen.

The following example demonstrates how to simulate a clinical scenario with a voxelized CT patient overlapping detector blocks using parallel worlds:


.. code:: python

    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_AIR"

    # patient
    ct = sim.add_volume("Image", "voxelized_ct")
    ct.image = "data/phantom.mha"
    ct.mother = "world"

    # create two other parallel worlds
    sim.add_parallel_world("parallel_world")

    # detector in w2 (on top of world)
    det = sim.add_volume("Box", "detector")
    det.mother = "parallel_world"
    det.material = "NaI"
    det.size = [400 * mm, 400 * mm, 40 * mm]
    det.translation = [0, 0, 100 * mm]

In this setup, the voxelized CT is placed in the primary world, representing the patient anatomy and the detector is placed in a parallel world to avoid conflicts with the CT volume.

Volume voxelization
-------------------

Tools to convert any volume into voxelized image (a matrix of voxels) is provided. It is described in  :ref:`Voxelization <voxelization>`.


Examples of complex geometries: Linac, SPECT, PET, phantoms
-----------------------------------------------------------

Examples of complex nested geometries, partly relying on boolean and
repeat operations, can be found in the subpackages
``opengate.contrib.pet``, ``opengate.contrib.spect``,
``opengate.contrib.linacs``, ``opengate.contrib.phantoms``. Also have a
look at some of the tests that use these geometries, e.g. ``test015``
(iec phantom), ``test019`` (linac Elekta), ``test028`` (SPECT GE NM670),
``test037`` (Philips Vereos PET).

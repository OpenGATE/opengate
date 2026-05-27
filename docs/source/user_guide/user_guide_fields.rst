How to: Electromagnetic fields
==============================

GATE provides an interface to define electromagnetic fields within simulation volumes. Under the hood, GATE configures Geant4's field tracking machinery (equation of motion, Runge-Kutta stepper, chord finder) for you.

Fields are defined as standalone objects, then attached to one or more volumes with ``add_field()``. Each volume can hold at most one field. A single field object can be shared across multiple volumes.

Fields are attached to logical volumes, so they automatically propagate to all physical placements of that volume. Dynamic geometry changes are supported: if a field is attached to a volume that is later moved or rotated, the field will move/rotate with it.

All field definitions are relative to the local coordinate system they are attached to. This means that, for instance, if a field is attached to a volume that is rotated, the field vector will be rotated accordingly.

Quick example
-------------

.. code-block:: python

   import opengate as gate
   from opengate.geometry import fields

   sim = gate.Simulation()
   tesla = gate.g4_units.tesla
   cm = gate.g4_units.cm

   box = sim.add_volume("Box", "magnet")
   box.size = [50 * cm, 50 * cm, 50 * cm]
   box.material = "G4_Galactic"

   field = fields.UniformMagneticField(name="B_field_for_box")
   field.field_vector = [0, 1 * tesla, 0]
   box.add_field(field)


Available field types
---------------------

Magnetic fields
~~~~~~~~~~~~~~~

**UniformMagneticField** -- Constant magnetic field throughout the volume. Uses the native Geant4 ``G4UniformMagField`` under the hood.

.. code-block:: python

   field = fields.UniformMagneticField(name="B_uniform")
   field.field_vector = [0, 0, 2 * tesla]   # [Bx, By, Bz] <- relative to the volume's local coordinate system
   box.add_field(field)

**QuadrupoleMagneticField** -- Quadrupole magnetic field defined via a field gradient. Uses the native Geant4 ``G4QuadrupoleMagField`` under the hood. The field is always oriented such that the optical axis is along the local Z direction of the volume and one of the south poles sits in the +XY quadrant.

.. code-block:: python

   field = fields.QuadrupoleMagneticField(name="B_quad")
   field.gradient = 10 * tesla / m   # field gradient (T/m)
   box.add_field(field)

**SextupoleMagneticField** -- Sextupole magnetic field defined via a field gradient. Uses the native Geant4 ``G4SextupoleMagField`` under the hood. The field is always oriented such that the optical axis is along the local Z direction of the volume and one of the north poles sits in the +Y direction.

.. code-block:: python

   field = fields.SextupoleMagneticField(name="B_sext")
   field.gradient = 10 * tesla / m   # field gradient (T/m)
   box.add_field(field)

**CustomMagneticField** -- Arbitrary magnetic field defined by a Python callback. The function receives ``(x, y, z, t)`` in Geant4 internal units and must return ``[Bx, By, Bz]``.

.. code-block:: python

   def my_B_field(x, y, z, t): # <- relative to the volume's local coordinate system
       # Spatially varying field
       return [0, (1 + x * z / m**2) * tesla, 0] # <- relative to the volume's local coordinate system

   field = fields.CustomMagneticField(name="B_custom")
   field.field_function = my_B_field
   box.add_field(field)

.. warning:: Performance warning

   Custom fields are evaluated via a Python callback for every field evaluation during tracking. This will significantly slow down the simulation. Prefer native types when possible. We are currently working on developing a faster custom field implementation. For more details, see :ref:`user_guide_fields_performance`.

**MappedMagneticField** -- Magnetic field defined by values on a regular 3D Cartesian grid. Field values are interpolated between grid points (trilinear by default). This is the recommended approach for importing fields from external calculations (e.g. finite element solvers) or for replacing a slow ``CustomMagneticField`` with a pre-sampled C++ equivalent.

The field is specified as a 2D array with columns ``[x, y, z, Bx, By, Bz]`` in Geant4 internal units. The grid must be regular (uniform spacing along each axis) and complete (every combination of the sampled x, y, z values must be present). All coordinates are in the local frame of the attached volume. Degenerate axes are not allowed, so the minimum valid grid is 2×2×2 (eight corner points).

.. code-block:: python

   import numpy as np

   # data.csv has columns: x, y, z (in mm), Bx, By, Bz (in T)
   mm = gate.g4_units.mm
   tesla = gate.g4_units.tesla

   field_matrix = np.loadtxt("data.csv", delimiter=",")
   field_matrix[:, :3] *= mm      # convert positions to Geant4 internal length units
   field_matrix[:, 3:] *= tesla   # convert field to Geant4 internal field units

   field = fields.MappedMagneticField(name="B_mapped")
   field.field_matrix = field_matrix
   box.add_field(field)

.. warning:: Points outside the grid

   If the grid does not cover the entire volume, field values will be extrapolated outside the grid using the nearest valid value (i.e. clamping to the edge). We recommend defining the grid to cover the entire volume to avoid unexpected behaviour.


Electric fields
~~~~~~~~~~~~~~~

**UniformElectricField** -- Constant electric field. Uses the native Geant4 ``G4UniformElectricField`` under the hood.

.. code-block:: python

   volt = gate.g4_units.volt
   m = gate.g4_units.m

   field = fields.UniformElectricField(name="E_uniform")
   field.field_vector = [1e6 * volt / m, 0, 0]   # [Ex, Ey, Ez] <- relative to the volume's local coordinate system
   box.add_field(field)

**CustomElectricField** -- Arbitrary electric field defined by a Python callback. The function receives ``(x, y, z, t)`` in Geant4 internal units and must return ``[Ex, Ey, Ez]``.

.. code-block:: python

   def my_E_field(x, y, z, t): # <- relative to the volume's local coordinate system
       return [1e6 * volt / m, 0, 0] # <- relative to the volume's local coordinate system

   field = fields.CustomElectricField(name="E_custom")
   field.field_function = my_E_field
   box.add_field(field)

.. warning:: Performance warning

   Same GIL overhead as ``CustomMagneticField``. See :ref:`user_guide_fields_performance`.

**MappedElectricField** -- Electric field defined on a regular 3D Cartesian grid, same interface as ``MappedMagneticField``. Columns are ``[x, y, z, Ex, Ey, Ez]``.

.. code-block:: python

   field = fields.MappedElectricField(name="E_mapped")
   field.field_matrix = field_matrix   # columns: [x, y, z, Ex, Ey, Ez], values in Geant4 internal units
   box.add_field(field)


Electromagnetic fields
~~~~~~~~~~~~~~~~~~~~~~

Combined magnetic and electric fields.

**UniformElectroMagneticField** -- Constant electromagnetic field. Uses the GATE C++ implementation ``GateUniformElectroMagneticField`` under the hood.

.. code-block:: python

   volt = gate.g4_units.volt
   m = gate.g4_units.m

   field = fields.UniformElectroMagneticField(name="EM_uniform")
   field.field_vector_B = [0, 0, 1 * tesla]          # [Bx, By, Bz] in local coordinates
   field.field_vector_E = [1e6 * volt / m, 0, 0]     # [Ex, Ey, Ez] in local coordinates
   box.add_field(field)

**CustomElectroMagneticField** -- Arbitrary combined field. The callback must return all six components ``[Bx, By, Bz, Ex, Ey, Ez]``.

.. code-block:: python

   def my_EM_field(x, y, z, t):
       return [0, 1 * tesla, 0, 1e6 * volt / m, 0, 0]

   field = fields.CustomElectroMagneticField(name="EM_custom")
   field.field_function = my_EM_field
   box.add_field(field)

.. warning:: Performance warning

   Same GIL overhead as ``CustomMagneticField``. See :ref:`user_guide_fields_performance`.

**MappedElectroMagneticField** -- Combined B and E field, each defined on its own independent regular 3D Cartesian grid. The two grids do not need to share the same resolution or spatial extent.

.. code-block:: python

   field = fields.MappedElectroMagneticField(name="EM_mapped")
   field.field_matrix_B = b_matrix   # columns: [x, y, z, Bx, By, Bz], values in Geant4 internal units
   field.field_matrix_E = e_matrix   # columns: [x, y, z, Ex, Ey, Ez], values in Geant4 internal units
   box.add_field(field)


Integration and accuracy parameters
--------------------------------

All field types inherit the following parameters that control the numerical integration of the equation of motion. The defaults are suitable for most cases, but they can be tuned for better accuracy or performance.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Default
     - Description
   * - ``stepper``
     - ``DormandPrince745``
     - Stepping algorithm used for integrating the equation of motion. See :ref:`steppers` for available options.
   * - ``step_minimum``
     - 0.01 mm
     - Minimum step size for the chord finder.
   * - ``delta_chord``
     - 0.001 mm
     - Maximum sagitta (miss distance between the chord approximation and the true curved trajectory).
   * - ``delta_one_step``
     - 0.001 mm
     - Positional accuracy per integration step.
   * - ``delta_intersection``
     - 0.0001 mm
     - Positional accuracy at volume boundaries.
   * - ``min_epsilon_step``
     - 1e-7
     - Minimum relative integration accuracy.
   * - ``max_epsilon_step``
     - 1e-5
     - Maximum relative integration accuracy.

Example:

.. code-block:: python

   field = fields.UniformMagneticField(name="B")
   field.field_vector = [0, 0, 1 * tesla]
   field.stepper = "DormandPrince745"
   field.delta_chord = 0.01 * mm
   field.step_minimum = 0.1 * mm
   box.add_field(field)


.. _steppers:

Steppers
~~~~~~~~

For general fields (electric and/or magnetic components):

- ``DormandPrince745`` (default)
- ``ClassicalRK4``
- ``CashKarpRKF45``
- ``BogackiShampine45``
- ``BogackiShampine23``
- ``DormandPrinceRK56``
- ``DormandPrinceRK78``

For purely magnetic fields, the following additional steppers are available:

- ``NystromRK4``
- ``ExactHelicalStepper``

Please refer to the `Geant4 documentation <https://geant4.web.cern.ch/documentation/pipelines/master/bfad_html/ForApplicationDevelopers/Detector/electroMagneticField.html>`__ for details on the characteristics and recommended use cases for each stepper type.



Attaching fields to volumes
----------------------------

Use ``add_field()`` to attach a field to a volume. The volume must already be added to the simulation.

.. code-block:: python

   box = sim.add_volume("Box", "my_box")
   # ...configure box and define field
   box.add_field(field)


**One field per volume.** Attempting to attach a second field raises an error.

**Shared fields.** The same field object can be attached to multiple volumes. This is useful when several volumes should have the same field configuration:

.. code-block:: python

   field = fields.UniformMagneticField(name="B_shared")
   field.field_vector = [0, 0, 1 * tesla]
   box1.add_field(field)
   box2.add_field(field)

**Unique names.** Field names must be unique across the simulation. Two different field objects with the same name will raise an error.

**Propagation to daughter volumes.** A field attached to a volume automatically propagates to all of its daughter volumes. A daughter volume can override this by attaching its own field. In that case, the parent's field stops at the daughter's boundary and the daughter's field is used inside. This mirrors standard Geant4 behaviour.

**Behaviour with repeated placements.** When a volume with a field is repeatedly placed (i.e. a logical volume with several physical placements), each physical instance will have the field in its own local coordinate system.

**Behaviour with dynamic geometry changes.** If a field is attached to a volume that is later moved or rotated, the field will move/rotate with it.

.. code-block:: python

   outer = sim.add_volume("Box", "outer")
   inner = sim.add_volume("Box", "inner")
   inner.mother = "outer"

   field_outer = fields.UniformMagneticField(name="B_outer")
   field_outer.field_vector = [0, 0, 1 * tesla]
   outer.add_field(field_outer)
   # "inner" inherits B_outer automatically.

   # To override it inside the daughter, attach a different field:
   field_inner = fields.UniformMagneticField(name="B_inner")
   field_inner.field_vector = [0, 2 * tesla, 0]
   inner.add_field(field_inner)
   # Now "inner" uses B_inner; "outer" still uses B_outer outside of "inner".


Visualizing fields
------------------

Geant4 can overlay field arrows on the visualization of the geometry. The Geant4 command is ``/vis/scene/add/magneticField <arrow density> <arrow type>`` (or ``/vis/scene/add/electricField`` for electric fields). It can be passed to GATE via the ``visu_commands`` parameter:

.. code-block:: python

   sim.visu = True
   sim.visu_type = "qt"
   sim.visu_commands.append("/vis/scene/add/magneticField 20 fullArrow")
   sim.visu_commands.append("/vis/scene/add/electricField 20 fullArrow")


.. _user_guide_fields_performance:

Performance: native vs custom fields
------------------------------------

Native field types (``UniformMagneticField``, ``UniformElectricField``, ``QuadrupoleMagneticField``, ``SextupoleMagneticField``, ``UniformElectroMagneticField``) are evaluated entirely in C++ by Geant4 (or GATE in the case of the uniform electromagnetic field). They have no Python overhead and are the recommended choice when they match your use case.

Custom fields (``CustomMagneticField``, ``CustomElectricField``, ``CustomElectroMagneticField``) call a Python function for **every evaluation** of ``GetFieldValue`` during tracking. This means that the GIL is acquired and released on every call, which can significantly slow down the simulation, especially in multithreaded mode where all threads serialize through the Python callback.

**Recommendation:** Use native types whenever possible. For spatially varying fields, use a mapped field type (``MappedMagneticField``, ``MappedElectricField``, ``MappedElectroMagneticField``): define the field on a grid once at setup and let the C++ interpolator handle all evaluations during tracking with zero Python overhead.

.. I am keeping this as a comment for now because sources are not serialized yet, so the round-trip for a full simulation object does not work.
.. Serialization
.. --------------

.. Non-custom fields are fully serializable via GATE's ``to_dictionary()`` / ``from_dictionary()`` mechanism:

.. .. code-block:: python

..    d = sim.to_dictionary()
..    sim2 = gate.Simulation()
..    sim2.from_dictionary(d)
..    # sim2 now has the same fields attached to the same volumes

.. Custom fields (those with a ``field_function`` callback) **cannot** be serialized.


Examples
--------

The field implementation is covered by the ``test099_fields_*`` tests in ``opengate/tests/src/geometry/``. These tests can be used as examples of how to define and use fields in GATE. They include:

- ``test099_fields_analytical_B`` -- Uniform B field vs analytical cyclotron radius.
- ``test099_fields_analytical_E`` -- Uniform E field vs analytical energy gain.
- ``test099_fields_custom_vs_native_B`` -- Custom trampoline B vs native G4 (bit-identical).
- ``test099_fields_custom_vs_native_E`` -- Custom trampoline E vs native G4 (bit-identical).
- ``test099_fields_mapped_vs_uniform_B`` -- MappedMagneticField (constant grid) vs UniformMagneticField.
- ``test099_fields_mapped_vs_uniform_E`` -- MappedElectricField (constant grid) vs UniformElectricField.
- ``test099_fields_multi_volume_refresh`` -- Uniform field shared across two volumes; one is dynamically rotated between runs.
- ``test099_fields_mapped_multi_volume_refresh`` -- Same as above with a MappedMagneticField.
- ``test099_fields_repeated_placements`` -- Uniform field on a single box vs the same total depth split into repeated slabs.
- ``test099_fields_mapped_repeated_placements`` -- Same as above with a MappedMagneticField.
- ``test099_fields_rotated_volume`` -- Uniform field shared between an unrotated and a rotated volume.
- ``test099_fields_mapped_rotated_volume`` -- Same as above with a MappedMagneticField.
- ``test099_fields_serialization`` -- Round-trip serialization for all non-custom types.
- ``test099_fields_api`` -- API guards.
- ``test099_fields_stepper_em`` -- Comparison of different steppers for a uniform E field.
- ``test099_fields_stepper`` -- Comparison of different steppers for a uniform B field.


Class reference
----------------

.. autoclass:: opengate.geometry.fields.FieldBase
   :members:
   :no-index:

.. autoclass:: opengate.geometry.fields.UniformMagneticField
   :members:

.. autoclass:: opengate.geometry.fields.QuadrupoleMagneticField
   :members:

.. autoclass:: opengate.geometry.fields.SextupoleMagneticField
   :members:

.. autoclass:: opengate.geometry.fields.CustomMagneticField
   :members:

.. autoclass:: opengate.geometry.fields.MappedMagneticField
   :members:

.. autoclass:: opengate.geometry.fields.UniformElectricField
   :members:

.. autoclass:: opengate.geometry.fields.CustomElectricField
   :members:

.. autoclass:: opengate.geometry.fields.MappedElectricField
   :members:

.. autoclass:: opengate.geometry.fields.UniformElectroMagneticField
   :members:

.. autoclass:: opengate.geometry.fields.CustomElectroMagneticField
   :members:

.. autoclass:: opengate.geometry.fields.MappedElectroMagneticField
   :members:

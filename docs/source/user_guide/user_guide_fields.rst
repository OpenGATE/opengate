How to: Electromagnetic fields
==============================

GATE provides an interface to define electromagnetic fields within simulation volumes. Under the hood, GATE configures Geant4's field tracking machinery (equation of motion, Runge-Kutta stepper, chord finder) for you.

Fields are defined as standalone objects, then attached to one or more volumes with :meth:`~opengate.geometry.volumes.VolumeBase.add_field`. Each volume can hold at most one field. A single field object can be shared across multiple volumes.

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
   field.field_vector = [0, 0, 2 * tesla]   # [Bx, By, Bz]
   box.add_field(field)

**QuadrupoleMagneticField** -- Quadrupole magnetic field defined via a field gradient. Uses the native Geant4 ``G4QuadrupoleMagField`` under the hood.

.. code-block:: python

   field = fields.QuadrupoleMagneticField(name="B_quad")
   field.gradient = 10 * tesla / m   # field gradient (T/m)
   box.add_field(field)

**CustomMagneticField** -- Arbitrary magnetic field defined by a Python callback. The function receives ``(x, y, z, t)`` in Geant4 internal units and must return ``[Bx, By, Bz]``.

.. code-block:: python

   def my_B_field(x, y, z, t):
       # Spatially varying field
       return [0, (1 + x * z / m**2) * tesla, 0]

   field = fields.CustomMagneticField(name="B_custom")
   field.field_function = my_B_field
   box.add_field(field)

.. warning:: Performance warning

   Custom fields are evaluated via a Python callback for every field evaluation during tracking. This will significantly slow down the simulation. Prefer native types when possible. We are currently working on developing a faster custom field implementation. For more details, see :ref:`user_guide_fields_performance`.


Electric fields
~~~~~~~~~~~~~~~

**UniformElectricField** -- Constant electric field. Uses the native Geant4 ``G4UniformElectricField`` under the hood.

.. code-block:: python

   volt = gate.g4_units.volt
   m = gate.g4_units.m

   field = fields.UniformElectricField(name="E_uniform")
   field.field_vector = [1e6 * volt / m, 0, 0]   # [Ex, Ey, Ez]
   box.add_field(field)

**CustomElectricField** -- Arbitrary electric field defined by a Python callback. The function receives ``(x, y, z, t)`` in Geant4 internal units and must return ``[Ex, Ey, Ez]``.

.. code-block:: python

   def my_E_field(x, y, z, t):
       return [1e6 * volt / m, 0, 0]

   field = fields.CustomElectricField(name="E_custom")
   field.field_function = my_E_field
   box.add_field(field)


Electromagnetic fields
~~~~~~~~~~~~~~~~~~~~~~

Combined magnetic and electric fields.

**CustomElectroMagneticField** -- Arbitrary combined field. The callback must return all six components ``[Bx, By, Bz, Ex, Ey, Ez]``.

.. code-block:: python

   def my_EM_field(x, y, z, t):
       return [0, 1 * tesla, 0, 1e6 * volt / m, 0, 0]

   field = fields.CustomElectroMagneticField(name="EM_custom")
   field.field_function = my_EM_field
   box.add_field(field)


Integration accuracy parameters
--------------------------------

All field types inherit the following parameters that control the numerical integration of the equation of motion. The defaults are suitable for most cases, but they can be tuned for better accuracy or performance.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Default
     - Description
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
   field.delta_chord = 0.01 * mm
   field.step_minimum = 0.1 * mm
   box.add_field(field)


Attaching fields to volumes
----------------------------

Use :meth:`~opengate.geometry.volumes.VolumeBase.add_field` to attach a field to a volume. The volume must already be added to the simulation.

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


.. _user_guide_fields_performance:

Performance: native vs custom fields
------------------------------------

Native field types (``UniformMagneticField``, ``UniformElectricField``, ``QuadrupoleMagneticField``) are evaluated entirely in C++ by Geant4. They have no Python overhead and are the recommended choice when they match your use case.

Custom fields (``CustomMagneticField``, ``CustomElectricField``, ``CustomElectroMagneticField``) call a Python function for **every evaluation** of ``GetFieldValue`` during tracking. This means that the GIL is acquired and released on every call, which can significantly slow down the simulation, especially in multithreaded mode where all threads serialize through the Python callback.

**Recommendation:** Use native types whenever possible.

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
- ``test099_fields_serialization`` -- Round-trip serialization for all non-custom types.
- ``test099_fields_api`` -- API guards.


Class reference
----------------

.. autoclass:: opengate.geometry.fields.FieldBase
   :members:

.. autoclass:: opengate.geometry.fields.UniformMagneticField
   :members:

.. autoclass:: opengate.geometry.fields.QuadrupoleMagneticField
   :members:

.. autoclass:: opengate.geometry.fields.CustomMagneticField
   :members:

.. autoclass:: opengate.geometry.fields.UniformElectricField
   :members:

.. autoclass:: opengate.geometry.fields.CustomElectricField
   :members:

.. autoclass:: opengate.geometry.fields.CustomElectroMagneticField
   :members:

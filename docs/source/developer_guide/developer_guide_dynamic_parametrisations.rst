Dynamic parametrisations
========================

Overview
--------

Dynamic parametrisations are the mechanism used in GATE to change the state of
an object from one ``G4Run`` to the next. Typical examples are:

- moving a volume by changing its translation,
- rotating a volume,
- changing the image of an ``ImageVolume``,
- changing the activity image of a ``VoxelSource``.

The user-facing logic is run-based: a simulation defines
``run_timing_intervals``, and a dynamic object provides one value per run for
every dynamic parameter. The framework then applies the appropriate state at
the beginning of each run.


General architecture
--------------------

The dynamic system has four main building blocks:

1. a dynamic object,
2. one or more changers,
3. a hidden dynamic actor,
4. engine-side wiring which creates and registers that actor.


Dynamic objects
~~~~~~~~~~~~~~~

Objects which support dynamic parametrisations inherit from
``DynamicGateObject`` in ``opengate/base.py``.

This base class provides:

- the read-only ``dynamic_params`` user info entry,
- the ``is_dynamic`` property,
- the ``dynamic_user_info`` property,
- the ``add_dynamic_parametrisation()`` method,
- validation against ``simulation.run_timing_intervals``,
- the ``create_changers()`` hook.

The central idea is that only parameters explicitly declared as dynamic are
accepted as dynamic user input. A parameter becomes dynamic when its
``user_info_defaults`` entry contains ``"dynamic": True``.

For example, in a class definition:

.. code-block:: python

   user_info_defaults = {
       "image": (
           None,
           {
               "doc": "Path to the image file",
               "is_input_file": True,
               "dynamic": True,
           },
       )
   }

When the user calls:

.. code-block:: python

   obj.add_dynamic_parametrisation(image=[value_run_0, value_run_1, ...])

``DynamicGateObject`` stores that information in ``dynamic_params``.


Processing of dynamic parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``DynamicGateObject.add_dynamic_parametrisation()`` performs a few useful tasks:

- it filters the provided keyword arguments so that only truly dynamic user
  parameters remain in the dynamic payload,
- any extra keys are moved to ``extra_params``,
- callable values are evaluated against
  ``simulation.run_timing_intervals``,
- each parametrisation is stored under a generated or user-provided name.

The consistency check is performed by
``check_if_dynamic_params_match_run_timing_intervals()``. It ensures that every
dynamic vector has the same length as the simulation's list of timing
intervals.


The ``auto_changer`` option
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dynamic parametrisations also support the special option ``auto_changer``.

This option is handled centrally by ``DynamicGateObject.process_dynamic_parametrisation()``
in the base class. It is not something each dynamic class needs to reimplement.

The default is:

.. code-block:: python

   auto_changer=True

This means:

- store the dynamic parametrisation as usual,
- and when ``create_changers()`` is called, use the default changer logic
  provided by the class.

In other words, ``auto_changer=True`` means "use the changer provided by this
class".

Examples:

- ``ImageVolume.create_changers()`` creates a ``VolumeImageChanger`` for a
  dynamic ``image`` parametrisation,
- ``VoxelSource.create_changers()`` creates a
  ``SourceActivityImageChanger`` for a dynamic source image.

If the user sets:

.. code-block:: python

   auto_changer=False

the dynamic values are still stored in ``dynamic_params``, but the class should
not automatically create its default changer for that parametrisation. This is
meant for advanced use cases where the user wants to provide a custom changer
manually.

A concrete example can be found in
``opengate/tests/src/geometry/test071_custom_geometry_changer.py``. That test
shows how to:

- derive a custom changer from ``GeometryChanger``,
- create a ``DynamicGeometryActor`` manually,
- add the custom changers to ``dynamic_geometry_actor.changers``.

The more elaborate example
``opengate/tests/src/actors/test030_dose_motion_dynamic_param_custom.py`` uses
the same idea for custom translation and rotation changers.


Changers
~~~~~~~~

Changers are small helper objects responsible for applying one concrete change
at runtime.

Examples already present in the code base are:

- ``VolumeTranslationChanger``
- ``VolumeRotationChanger``
- ``VolumeImageChanger``
- ``SourceActivityImageChanger``

All changers inherit from ``ChangerBase`` in
``opengate/actors/dynamicactors.py``. There are two specialized branches:

- ``GeometryChanger`` for volumes,
- ``SourceChanger`` for sources.

Each changer has an ``apply_change(run_id)`` method. This method is called at
the beginning of every run and is responsible for applying the state
corresponding to that run.

The ``attached_to`` user parameter of changers is handled like other GateObject
parameters and becomes a generated property when ``process_cls()`` is called on
the changer class.


Dynamic actors
~~~~~~~~~~~~~~

The actual runtime update is performed by hidden actors:

- ``DynamicGeometryActor``
- ``DynamicSourceActor``

Both derive from ``DynamicActorBase`` in
``opengate/actors/dynamicactors.py`` and register the Geant4 hook
``BeginOfRunActionMasterThread``.

At the beginning of each run, the actor loops over its list of changers and
calls ``apply_change(run_id)``.

For geometry, ``DynamicGeometryActor`` may temporarily open and close the
geometry around the update. For sources, ``DynamicSourceActor`` simply forwards
the run id to its changers.


Engine-side wiring
~~~~~~~~~~~~~~~~~~

The engines create the hidden dynamic actors automatically.

For volumes:

- ``VolumeEngine.initialize_dynamic_parametrisations()``
- iterates over ``volume_manager.dynamic_volumes``
- validates their dynamic parameter lengths
- creates a ``DynamicGeometryActor`` if needed
- collects changers from ``volume.create_changers()``

For sources:

- ``SourceEngine.initialize_dynamic_parametrisations()``
- iterates over ``source_manager.dynamic_sources``
- validates their dynamic parameter lengths
- creates a ``DynamicSourceActor`` if needed
- collects changers from ``source.create_changers()``

So the usual pattern is:

1. mark a user parameter as dynamic,
2. let the object expose changers via ``create_changers()``,
3. let the engine instantiate the corresponding hidden actor.


Examples in the existing code base
----------------------------------

Dynamic geometry
~~~~~~~~~~~~~~~~

``VolumeBase`` supports dynamic translation and rotation. ``ImageVolume`` adds
support for a dynamic ``image`` parameter.

The ``ImageVolume`` implementation is a good example of a full dynamic object:

- ``image`` is declared with ``dynamic=True``,
- ``create_changers()`` builds a ``VolumeImageChanger``,
- the changer switches the label image at run boundaries,
- ``DynamicGeometryActor`` applies the change in
  ``BeginOfRunActionMasterThread``.


Dynamic voxel source
~~~~~~~~~~~~~~~~~~~~

``VoxelSource`` supports a dynamic ``image`` parameter for the activity map.

The implementation follows the same pattern:

- ``image`` is declared dynamic,
- ``VoxelSource.create_changers()`` creates a
  ``SourceActivityImageChanger``,
- the changer calls ``VoxelSource.update_activity_image(...)``,
- the source reloads the image, updates geometry information, and recomputes
  its CDFs,
- ``DynamicSourceActor`` applies the change at the beginning of each run.


How to make a parameter dynamic
-------------------------------

This section describes the minimal steps needed to make a parameter dynamic in a
new object type.


1. Inherit from ``DynamicGateObject``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the class is not already dynamic, make it inherit from ``DynamicGateObject``
or from a parent class which already does so.

This gives the class access to:

- ``add_dynamic_parametrisation()``
- ``dynamic_params``
- ``create_changers()``


2. Mark the parameter as dynamic in ``user_info_defaults``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the ``user_info_defaults`` entry of the parameter, add:

.. code-block:: python

   "dynamic": True

Example:

.. code-block:: python

   user_info_defaults = {
       "my_parameter": (
           default_value,
           {
               "doc": "Description of the parameter.",
               "dynamic": True,
           },
       )
   }

Without this flag, ``add_dynamic_parametrisation(my_parameter=...)`` will not
store the parameter as dynamic input.


3. Implement the runtime change in ``apply_change()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The actual runtime entry point is the changer method:

.. code-block:: python

   def apply_change(self, run_id):
       ...

This method is called by the hidden dynamic actor at the beginning of each run.
Its job is to apply the state corresponding to ``run_id``.

There are two common patterns:

- the changer performs the update directly,
- the changer delegates to a dedicated update method on the object side.

Two concrete examples from the current code base:

Volume-side example: direct update in the changer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For dynamic translations and rotations, the update is performed directly inside
the changer. The changer resolves the target physical volume and applies the
new Geant4 transform for the current run.

For example, ``VolumeTranslationChanger.apply_change()`` does:

.. code-block:: python

   def apply_change(self, run_id):
       if self.g4_physical_volume is None:
           self.g4_physical_volume = self.attached_to_volume.get_g4_physical_volume(
               self.repetition_index
           )
       self.g4_physical_volume.SetTranslation(self.g4_translations[run_id])

This is a good pattern when the change is local and simple:

- prepare Geant4-compatible values in ``initialize()``,
- resolve the target G4 object lazily,
- apply the run-specific value directly in ``apply_change(run_id)``.

Source-side example: delegate to an object update method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For ``VoxelSource``, changing the dynamic ``image`` parameter is heavier than a
simple assignment because the source sampling machinery depends on the image
content. In that case, the changer delegates to a method implemented on the
object itself.

``SourceActivityImageChanger.apply_change()`` does:

.. code-block:: python

   def apply_change(self, run_id):
       self.attached_to_source.update_activity_image(self.activity_images[run_id])

The actual work is then performed by
``VoxelSource.update_activity_image(filename)``, which:

- loads the new ITK image,
- updates the image transform information used by the C++ position generator,
- recomputes the cumulative distribution functions.

Conceptually:

.. code-block:: python

   def update_activity_image(self, filename):
       self._current_itk_image = itk.imread(ensure_filename_is_str(filename))
       self.set_transform_from_user_info()
       self.cumulative_distribution_functions()

This is a good pattern when the update requires more than a simple runtime
assignment, for example:

- loading a new image,
- refreshing derived metadata,
- rebuilding cached lookup tables or CDFs,
- pushing image information to C++ objects.


4. Implement or extend ``create_changers()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``create_changers()`` is where the object translates stored dynamic
parametrisations into changer instances.

Typical pattern:

.. code-block:: python

   def create_changers(self):
       changers = super().create_changers()
       for dp in self.dynamic_params.values():
           if dp["extra_params"]["auto_changer"] is True:
               if "my_parameter" in dp:
                   changers.append(
                       MyParameterChanger(
                           name=f"{self.name}_my_parameter_changer_{len(changers)}",
                           attached_to=self,
                           simulation=self.simulation,
                           values=dp["my_parameter"],
                       )
                   )
       return changers

If ``auto_changer`` is set to ``False``, the user is responsible for creating
and wiring the changer manually.


5. Implement the changer class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The changer should inherit from either ``GeometryChanger`` or ``SourceChanger``
when possible, or from ``ChangerBase`` if neither fits.

Minimal example:

.. code-block:: python

   class MyParameterChanger(GeometryChanger):
       user_info_defaults = {
           "values": (
               None,
               {
                   "doc": "One value per run.",
               },
           ),
       }

       def apply_change(self, run_id):
           self.attached_to_volume.update_my_parameter(self.values[run_id])


6. Call ``process_cls()`` on the new class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Like other GateObject-derived classes, changer classes must be processed by the
class factory mechanism:

.. code-block:: python

   process_cls(MyParameterChanger)

This step creates the GateObject-style properties from ``user_info_defaults``.
Without it, parameters such as ``attached_to`` or ``values`` will not behave as
expected.


7. Make sure the relevant engine knows how to instantiate the hidden actor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your object is a volume or a source and you reuse the existing
``DynamicGeometryActor`` or ``DynamicSourceActor``, no new engine logic is
needed beyond returning changers from ``create_changers()``.

If you introduce a new family of dynamic objects, you will need the equivalent
of:

- a manager property like ``dynamic_sources`` or ``dynamic_volumes``,
- an engine method which validates dynamic parameter lengths,
- creation of a hidden actor,
- collection of changers from the dynamic objects.


Common pitfalls
---------------

Initialization order
~~~~~~~~~~~~~~~~~~~~

Be careful with checks which run before ``G4RunManager.Initialize()``.

For example, actor initialization currently happens before geometry
construction. If a check touches geometry- or image-dependent properties too
early, it may observe a partially initialized object. A concrete example is a
check on an attached ``ImageVolume`` which touches image-derived properties
before ``ImageVolume.construct()`` has loaded the input image.


Validation
~~~~~~~~~~

Do not forget to validate the number of dynamic values against
``run_timing_intervals``. The framework already provides this through
``check_if_dynamic_params_match_run_timing_intervals()``, but the relevant
engine must call it.


Keep the changer small
~~~~~~~~~~~~~~~~~~~~~~

The changer should usually only:

- resolve the target object,
- pick the value corresponding to ``run_id``,
- call a well-defined update method on that object.

Heavy logic is usually better kept in the object itself.


Summary
-------

To make a parameter dynamic:

1. make sure the object is a ``DynamicGateObject``,
2. mark the parameter with ``dynamic=True``,
3. implement the runtime update logic on the object,
4. expose one or more changers via ``create_changers()``,
5. process the changer class with ``process_cls()``,
6. rely on the engine to create a hidden dynamic actor which applies the
   changes at ``BeginOfRunActionMasterThread``.

This architecture keeps the user-facing API simple while keeping the runtime
logic generic and reusable.

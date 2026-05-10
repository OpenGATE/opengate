How to implement an auxiliary attribute
=======================================

Overview
--------

Auxiliary attributes are simulation-level objects that store and expose
track-associated state across multiple steps. They are useful whenever a value
cannot be obtained from the current step alone, for example:

- number of times a process occurred so far
- last process seen in a volume
- last interaction position
- future per-track state/history needed by actors or filters

An auxiliary attribute has two sides:

1. a Python-side class in ``opengate/auxiliary_attributes.py``
2. a C++-side class derived from ``GateVAuxiliaryAttribute``

The C++ class is responsible for:

- declaring Geant4 hooks such as ``SteppingAction()``
- storing/retrieving track information
- exposing the runtime value through typed getters
- optionally registering a DigiAttribute view for ROOT-based output


When to use an auxiliary attribute
----------------------------------

Use an auxiliary attribute when you need a value that must persist along a
track and evolve over time.

Do **not** use a plain DigiAttribute if the value:

- depends on previous steps
- must be propagated to secondaries
- must be reused by filters or non-ROOT actors


Basic architecture
------------------

The current architecture is:

.. code-block:: text

   Simulation
     -> auxiliary_attributes (Python objects)
     -> SimulationEngine.initialize_auxiliary_attributes()
       -> C++ GateVAuxiliaryAttribute objects
       -> registration into tracking / stepping actions

At runtime:

.. code-block:: text

   GateTrackingAction / GateSteppingAction
     -> dispatch hook calls to GateVAuxiliaryAttribute instances
     -> attributes update per-track auxiliary track information

Consumers can access auxiliary attributes in two ways:

1. through a DigiAttribute/ROOT-backed branch
2. directly at runtime from C++ using the auxiliary-attribute registry and
   typed getters


Implementing the Python-side class
----------------------------------

The Python-side class should mirror the actor pattern.

Minimal structure:

.. code-block:: python

   class MyAuxiliaryAttribute(
       AuxiliaryAttributeBase, g4.GateMyAuxiliaryAttribute
   ):

       user_info_defaults = {
           "some_parameter": (None, {"doc": "Explain parameter."}),
       }

       def __init__(self, *args, **kwargs):
           AuxiliaryAttributeBase.__init__(self, *args, **kwargs)
           self.__initcpp__()

       def __initcpp__(self):
           g4.GateMyAuxiliaryAttribute.__init__(self, self.user_info)

       def initialize(self):
           if self.some_parameter is None:
               fatal(
                   f"Auxiliary attribute '{self.name}' requires "
                   "some_parameter before initialization."
               )
           AuxiliaryAttributeBase.initialize(self)


Important rules:

1. Inherit first from ``AuxiliaryAttributeBase`` and then from the C++ class.
2. Implement ``__initcpp__()`` and call the C++ constructor there.
3. Do **not** call the C++ constructor only in ``__init__()``.
4. Use explicit base-class calls instead of ``super()`` across the Python/C++
   boundary.

Finally, register the class in ``auxiliary_attribute_types``.


Implementing the C++-side class
-------------------------------

The C++ class must derive from ``GateVAuxiliaryAttribute``.

Typical structure:

.. code-block:: cpp

   class GateMyAuxiliaryAttribute : public GateVAuxiliaryAttribute {
   public:
     explicit GateMyAuxiliaryAttribute(py::dict &user_info);

     void InitializeUserInfo(py::dict &user_info) override;
     void InitializeCpp() override;
     void SteppingAction(const G4Step *step) override;

     int GetIValue(const G4Step *step) const override;

   protected:
     std::string fVolumeName;
   };


In the constructor, typically:

- set ``fDigiAttributeType``
- declare implemented actions in ``fActions``

Example:

.. code-block:: cpp

   GateMyAuxiliaryAttribute::GateMyAuxiliaryAttribute(py::dict &user_info)
       : GateVAuxiliaryAttribute(user_info) {
     fDigiAttributeType = 'I';
     fActions.insert("SteppingAction");
   }


Storing per-track information
-----------------------------

Persistent per-track state is stored using ``G4VAuxiliaryTrackInformation``.

OpenGATE currently provides generic typed holders in:

- ``GateAuxiliaryTrackInformation.h``

Examples:

- ``GateIntAuxiliaryTrackInformation``
- ``GateStringAuxiliaryTrackInformation``
- ``GateThreeVectorAuxiliaryTrackInformation``
- ``GateIntegerCounterAuxiliaryTrackInformation``

Use the helpers from ``GateVAuxiliaryAttribute``:

- ``GetAuxiliaryTrackInformation<T>(track)``
- ``GetOrCreateAuxiliaryTrackInformation<T>(track)``
- ``GetAuxiliaryTrackInformationStoredValue<T, V>(step, default)``
- ``SetAuxiliaryTrackInformationStoredValue<T, V>(track, value)``
- ``PropagateAuxiliaryTrackInformationToSecondariesInCurrentStep<T>(step)``


Example: integer counter
------------------------

.. code-block:: cpp

   void GateMyCounterAttribute::SteppingAction(const G4Step *step) {
     auto *info = GetOrCreateAuxiliaryTrackInformation<
         GateIntegerCounterAuxiliaryTrackInformation>(step->GetTrack());
     info->Increment();
   }

   int GateMyCounterAttribute::GetIValue(const G4Step *step) const {
     return GetAuxiliaryTrackInformationValue<
         GateIntegerCounterAuxiliaryTrackInformation, int>(
         step, 0, &GateIntegerCounterAuxiliaryTrackInformation::GetCount);
   }


Example: string value
---------------------

.. code-block:: cpp

   void GateMyStringAttribute::SteppingAction(const G4Step *step) {
     SetAuxiliaryTrackInformationStoredValue<
         GateStringAuxiliaryTrackInformation, std::string>(
         step->GetTrack(), "my_value");
   }

   std::string GateMyStringAttribute::GetSValue(const G4Step *step) const {
     return GetAuxiliaryTrackInformationStoredValue<
         GateStringAuxiliaryTrackInformation, std::string>(
         step, "default");
   }


Declaring hooks
---------------

Auxiliary attributes declare which Geant4 hooks they implement by adding names
to ``fActions``.

Currently relevant examples:

- ``"SteppingAction"``
- ``"PreUserTrackingAction"``
- ``"PostUserTrackingAction"``

These are then registered into the appropriate action aggregators by the
simulation engine.


Volume-based auxiliary attributes
---------------------------------

If the attribute applies to a configured volume hierarchy, use the helper:

- ``IsStepInVolume(step, volume_name)``

from ``GateVAuxiliaryAttribute``.

This currently checks the touchable ancestry recursively.

Note: there is a TODO in the code to optimize this later, likely by introducing
a volume-sensitive auxiliary-attribute base class that precomputes descendant
logical volumes.


Propagating state to secondaries
--------------------------------

If the attribute should represent state accumulated up to the current point of
the track genealogy, propagate it in ``SteppingAction()`` using:

.. code-block:: cpp

   if (fPropagateFromParentTrack) {
     PropagateAuxiliaryTrackInformationToSecondariesInCurrentStep<
         GateIntegerCounterAuxiliaryTrackInformation>(step);
   }

This copies the current snapshot to secondaries created in the current step.

This is the correct mechanism when daughters created at different moments
should inherit different values.


Exposing the value to ROOT-based actors
---------------------------------------

If the attribute should be usable in ROOT-backed actors such as
``PhaseSpaceActor``, register a DigiAttribute view in ``InitializeCpp()``.

Example:

.. code-block:: cpp

   void GateMyAuxiliaryAttribute::InitializeCpp() {
     GateVAuxiliaryAttribute::InitializeCpp();

     auto fill = [=](GateVDigiAttribute *att, G4Step *step) {
       att->FillIValue(GetIValue(step));
     };

     auto *manager = GateDigiAttributeManager::GetInstance();
     manager->DefineDigiAttribute(fName, fDigiAttributeType, fill);
   }

Then the user can request the attribute by name in a PhaseSpace actor:

.. code-block:: python

   aux = sim.activate_auxiliary_attribute(
       "InteractionCounterAttribute",
       "InteractionCount__compt",
   )
   aux.process_name = "compt"

   phsp = sim.add_actor("PhaseSpaceActor", "phsp")
   phsp.attributes = ["KineticEnergy", aux.name]


Accessing an auxiliary attribute from a non-ROOT actor
------------------------------------------------------

This is one of the main reasons the auxiliary-attribute runtime getter API and
registry were introduced.

The basic pattern is:

1. the actor stores the auxiliary attribute name in Python user info
2. the actor resolves a non-owning ``GateVAuxiliaryAttribute*`` in C++
3. the actor calls the appropriate typed getter at runtime

Example C++ member:

.. code-block:: cpp

   GateVAuxiliaryAttribute *fAuxiliaryAttribute{nullptr};

Resolve it during initialization:

.. code-block:: cpp

   void GateMyActor::InitializeCpp() {
     GateVActor::InitializeCpp();
     fAuxiliaryAttribute =
         GateVAuxiliaryAttribute::GetAuxiliaryAttributeByName(
             fAuxiliaryAttributeName);
     if (fAuxiliaryAttribute == nullptr) {
       Fatal("Cannot find auxiliary attribute '" + fAuxiliaryAttributeName + "'.");
     }
   }

Use it at runtime:

.. code-block:: cpp

   void GateMyActor::SteppingAction(G4Step *step) {
     const auto n = fAuxiliaryAttribute->GetIValue(step);
     // use n in voxel filling or other runtime logic
   }

This is appropriate for:

- voxel actors
- dose-like actors
- runtime scorers
- any non-ROOT logic that needs per-track state


Accessing an auxiliary attribute from a filter
----------------------------------------------

This is already supported through the generic attribute comparison filter.

User syntax remains:

.. code-block:: python

   F = GateFilterBuilder()
   actor.filter = F.MyAuxiliaryAttribute > 0

Internally, ``GateAttributeComparisonFilter`` now resolves names against:

1. the auxiliary-attribute registry
2. then the classic DigiAttribute machinery as fallback

So the user-facing sugar syntax does not change.


Typed runtime getters
---------------------

``GateVAuxiliaryAttribute`` exposes typed runtime getters:

- ``GetDValue(const G4Step *)``
- ``GetIValue(const G4Step *)``
- ``GetLValue(const G4Step *)``
- ``GetSValue(const G4Step *)``
- ``Get3Value(const G4Step *)``
- ``GetUValue(const G4Step *)``

Concrete auxiliary attributes should override exactly the getter matching their
public value type.

These getters are now the main bridge for:

- ROOT-backed output
- filters
- non-ROOT actors


Lifecycle and ownership
-----------------------

Important design points:

- the auxiliary attribute registry is **non-owning**
- ownership remains with the simulation-side objects
- consumers should cache only non-owning pointers
- cached pointers are valid only during the engine lifetime
- the registry is cleared during engine teardown

This is important for anything that resolves attributes by name at
initialization time.


Checklist for a new auxiliary attribute
---------------------------------------

1. Add the C++ header and source deriving from ``GateVAuxiliaryAttribute``.
2. Add or reuse a suitable track-information type.
3. Implement ``InitializeUserInfo()``.
4. Implement ``InitializeCpp()``.
5. Implement the required Geant4 hooks.
6. Override the typed runtime getter matching the exposed value type.
7. Add the pybind binding.
8. Add the Python-side class in ``opengate/auxiliary_attributes.py``.
9. Register it in ``auxiliary_attribute_types``.
10. Add a test:

   - direct output through a ROOT-backed actor, if applicable
   - and/or runtime consumption from a filter or another actor


See also
--------

- ``docs/source/developer_guide/developer_guide_how_to_implement.rst``
- ``docs/source/developer_guide/developer_guide_init_actors.rst``

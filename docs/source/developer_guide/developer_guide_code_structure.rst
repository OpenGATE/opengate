Architecture: Managers and Engines
==================================

GATE 10 has two distinct kinds of classes which handle a simulation.
Managers provide an interface to the user to set-up and configure a
simulation and collect and organize user parameters in a structured way.
Engines provide the interface with Geant4 and are responsible for
creating all Geant4 objects. Managers and engines are divided in
sub-managers and sub-engines responsible for certain logical parts of a
simulation. Additionally, many objects in GATE are now implemented as
classes which provide interfaces to the managers and engines.

The ``Simulation`` class is the main manager with which the user
interacts. It collects general parameters, e.g. about verbosity and
visualization and it manages the way the simulation is run (in a
subprocess or not). Sub-managers are: ``VolumeManager``,
``PhysicsManager`` , ``ActorManager``, ``SourceManager``. These managers
can be thought of as bookkeepers. For example, the ``VolumeManager``
keeps a dictionary with all the volumes added to a simulation, a
dictionary with all the parallel world volumes, etc. But it also
provides the user with methods to perform certain tasks,
e.g. ``VolumeManager.add_parallel_world()``.

The ``SimulationEngine`` is the main driver of the Geant4 simulation:
every time the user calls ``sim.run()``, the ``Simulation`` object (here
assumed to be called ``sim``) creates a new ``SimulationEngine`` which
in turn creates all the sub-engines: ``VolumeEngine``,
``PhysicsEngine``, ``SourceEngine``, ``ActorEngine``, ``ActionEngine``.
The method ``SimulationEngine.run_engine()`` actually triggers the
construction and run of the Geant4 simulation. It takes the role of the
``main.cc`` in a pure Geant4 simulation. When the Geant4 simulation has
terminated, ``SimulationEngine.run_engine()`` returns the simulation
output which is then collect by the ``Simulation`` object and remains
accessible via ``sim.output``.

It is important to understand that the engines only exist while the
GATE/Geant4 simulation is running, while the managers exist during the
entire duration of the python interpreter session in which the user is
setting up the simulation.

The managers and engines are explained in more detail below.

References among managers and engines
-------------------------------------

Managers and engines frequently need to access attributes of other
managers and engines. They therefore need references to each other. In
GATE, these references follow a hierarchical pattern:

-  Sub-managers keep a references to the ``Simulation`` (the main
   manager). Sub-sub-managers keep references to the sub-manager above
   them. For example: ``PhysicsManager.simulation`` refers to the
   ``Simulation`` object which created it, and
   ``PhysicsListManager.physics_manager`` refers to the
   ``PhysicsManager`` which created it.
-  Objects created through a manager keep a reference to the creating
   manager. For example: all volumes have an attribute
   ``volume_manager``.
-  In a similar fashion, sub-engines keep a references to the
   ``SimulationEngine`` from which they originate.
-  The ``SimulationEngine`` itself keeps a reference to the
   ``Simulation`` which created it.

This hierarchical network of references allows reaching objects from any
other object. For example: a ``Region`` object is managed by the
``PhysicsManager``, so from a region, a volume can be reached via:

.. code:: python

   my_volume = region.physics_manager.simulation.volume_manager.get_volume('my_volume')

--------------

Geant4 bindings
===============

This repository contains C++ source code that maps some (not all!)
Geant4 classes into one single Python module. It also contains
additional C++ classes that extends Geant4 functionalities (also mapped
to Python). At the end of the compilation process a single Python module
is available, named ``opengate_core`` and is ready to use from the
Python side.

The source files are divided into two folders: ``g4_bindings`` and
``opengate_lib``. The first contains pure Geant4 Python bindings allow
to expose in Python a (small) part of Geant4 classes and functions. The
bindings are done with the
`pybind11 <https://github.com/pybind/pybind11>`__ library. The second
folder contains specific opengate functionalities.

How to add a Geant4 bindings ?
------------------------------

If you want to expose another Geant4 class (or functions), you need to:

-  Create a ``pyG4MyClass.cpp``
-  With a function ``init_G4MyClass`` (see example in the
   ``g4_bindings`` folder)
-  In this function, indicate all functions/members that you want to
   expose.
-  Declare and call this init function in the ``opengate_core.cpp``
   file.

Philosophy behind objects implemented as GateObject
===================================================

Generally, the idea is to encapsulate functionality into classes rather
than spreading out the code across managers and engines. The advantage
is that the code structure remains less cluttered. Good examples are the
``Region`` class and, although more complex, the volume classes. In the
following, we explain the rationale and design concept. For instructions
on how to implement or extend a class, see
`here <#how-a-class-in-gate-10-is-usually-set-up>`__.

The GATE classes representing and a Geant4 object (or multiple Geant4
objects combined) are meant to do multiple things: 1) Be a storage for
user parameters. Exmample: the ``Region`` class holds the user_info
``user_limits``, ``production_cuts``, and ``em_switches``. 2) Provide
interface functions to manager classes (and the user) to configure the
object or inquire about it. Examples: ``Region.associate_volume()``,
``Region.need_step_limiter()`` 3) Provide interface functions such as
``initialize()`` and ``close()`` to the engines to handle the Geant4
objects. 4) Provide convenience functionality such as dumping as
dictionary (``to_dictionary()``, ``from_dictionary()``), dump info about
the object (e.g. ``Region.dump_production_cuts()``), clone itself. 5)
Handle technical aspects such as pickling (for subprocesses) in a
unified way (`via the method
``__getstate__()`` <#implement-a-getstate-method-if-needed>`__)

The managers and engines, on the other hand, remain quite sleek and
clean. For example, if you look at the ``PhysicsEngine`` class, you find
the method

.. code:: python

       def initialize_regions(self):
           for region in self.physics_manager.regions.values():
               region.initialize()

which really just iterates over the regions and initializes them.

The advantage of this becomes evident especially if there are multiple
variants of a class (via inheritance), such as for volumes. In this
case, the ``VolumeEngine`` does not care about the specific type of
volume because it always calls the same interface. For example,
``VolumeEngine.Construct()`` (which is triggered by the G4RunManager,
not GATE) iterates over the volumes and calls ``volume.construct()``.
The volume object then takes care of taking the correct actions. If the
code inside each volume’s ``construct()`` method were implemented inside
``VolumeEngine.Construct()``, it would be cluttered with if statements
to pick what should be done.

   | **Note**
   | For now, only a part of GATE implements objects based on the
     GateObject base class. Actors and Sources still need to be
     refactored.

How a class in GATE 10 is (usually) set up:
===========================================

Naming convention
-----------------

-  Use small letters and underscores for python variables. Do **not**
   use capital letters and camelcase.
-  Use capital letters and camel case for overloaded C++ variables if
   the class inherits from a base class implemented in C++.
-  All attributes pointing to Geant4 objects should have a “g4\_”
   prepended for easy identification. Example:
   ``self.g4_logical_volume``.
-  Group the ``g4_***`` definitions in one block for better visual
   reference.

``__init__()`` method
---------------------

-  Define all attributes of the object in the ``__init__()`` method even
   if their value is set only later/elsewhere.

-  If no value is set in ``__init__()``, do:

   .. code:: python

      self.my_attribute = None

-  By defining all attributes in the ``__init__()`` method, other
   developers can easily inspect the class without reading through the
   entire class. Think of it as a C++ header file.

-  If your class inherits from another class, and in particular from
   ``GateObject`` or ``DynamicGateObject``, include wild card arguments
   and keyword arguments in your ``__init__()`` method:

   .. code:: python

      def __init__(self, your_specific_arguments, *args, your_specific_kwargs, **kwargs):
          super().__init__(*args, **kwargs)
          # ... YOUR CODE...

User info: handling parameters set by the user
----------------------------------------------

If your class handles user input, let it inherit from GateObject, or
DynamicGateObject if applicable. Define and configure user input via the
``user_info_defaults`` class attribute. See section XXX.

**Important**: User input defined and configured in the
``user_info_defaults`` dictionary should generally not be handled
manually in your ``__init__()`` method. They are passed on to the
superclass inside the ``kwargs`` dictionary. See section XXX for more
detail.

Initialization of Geant4 objects
--------------------------------

Implement an ``initialize()`` method if Geant4 objects need to be
created by the SimulationEngine (or a sub-engine) when the simulation is
launched. The ``initialize()`` method should not take any arguments, but
only rely on object attributes (``self.xyz``) which were previously set.

Exception: G4RunManager has an initializatin sequence which GATE relies
on. In certain classes, the ``g4_XXX`` componentes are initialized as
part of this sequence on the C++ side. Example: All volumes implement a
``construct()`` method which is called when the G4RunManager calls the
overloaded ``Construct()`` method of the VolumeEngine.

Implement a ``close()`` method if needed
----------------------------------------

Explanation: If your class has attributes that point to Geant4 objects
which are deleted by the G4RunManager at the end of a simulation, your
class must get rid of these references when the SimulationEngine closes
down. This is achieved by a hierarchy of calls to a close() method,
starting from ``SimulationEngine.close()``. In your ``close()`` method,
set all attributes pointing to Geant4 objects which the G4RunManafger
will delete to ``None``. If your class manages a list of other objects
which themselves need to call their ``close()`` method, add a loop to
your ``close()`` method and close down the list members. If you inherit
from another class, do not forget to call the ``close()`` method from
the superclass via ``super().close()``. Take a look at
``VolumeManager.close()`` and the volumes classes or
``PhysicsManager.close()`` and the ``Region`` class for examples.

Implement a ``__getstate__()`` method if needed.
------------------------------------------------

Explanation: When a GATE simulation is run in a subprocess, all objects
need to be serialized so they can be sent to the subprocess, where they
are deserialized. The serialization is currently handled by the
``pickle`` module. If your class contains attributes which refer to
objects which cannot be pickled, the serialization will fail. This
typically concerns Geant4 objects. To make your class pickleable, you
should implement a ``__getstate__()`` method. This is essentially a hook
called within the serialization pipeline which returns a representation
of your object (usually a dictionary). You should remove items which
cannot be pickled from this dictionary.

**Example**: Assume your class has an attribute ``self.g4_funny_object``
referring to a Geant4 object. Your ``__getstate__()`` method should do
something like this:

.. code:: python

   def __getstate__(self):
       return_dict = self.__dict__
       return_dict['g4_funny_object'] = None
       return return_dict

If your class inherits from another one, e.g. from GateObject, you
should call the ``__getstate__()`` method from the superclass:

.. code:: python

   def __getstate__(self):
       return_dict = super().__getstate__()
       return_dict['g4_funny_object'] = None
       return return_dict

**Important**: The ``__getstate__()`` method should **not** change your
object, but only modify the dictionary to be returned. Therefore, avoid
``self.g4_funny_object = None`` as this also alters your object.

Important: Do **not** use the ``close()`` method in your
``__getstate__()`` method. The ``close()`` method is part of `another
mechanism <#implement-a-close-method-if-needed->`__ and these mechanisms
should not be entangled. And: the ``close()`` method would alter your
object and not only the returned dictionary representation.

Optional: Implement a ``__str__()`` method
------------------------------------------

You might consider implementing a ``__str__()`` method which, by
construction, is required to return a string. If implemented, this
method is called when the user places your object inside a ``print()``
statement: ``print(my_object)``. You could implement the ``__str__()``
method to provide useful information about your object. If your object
inherits from another class, call the superclass:

.. code:: python

   def __str__(self):
       s = super().__str__()
       s += "*** Additional info: ***\n"
       s += f"The object as an attribute 'xyz' of value {self.xyz}.\n"
       return s

In particular, the GateObject superclass (and variants) implement a
``__str__()`` method which lists all user_info of the object.

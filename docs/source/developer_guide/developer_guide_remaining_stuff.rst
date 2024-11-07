Helpers
=======

Error handling. Use the following to fail with an exception and trace:

.. code-block:: python

    import opengate as gate

    gate.raise_except('There is bug')
    gate.exception.fatal('This is a fatal error')
    gate.exception.warning('This is a warning')

There are several levels: `WARNING INFO DEBUG`. The last one prints more information. Logging is handled with logger in `helpers_log.py`.

Engines
=======

As explained `above <#gate-architecture-managers-and-engines>`_, the Engine classes drive the actual Geant4 simulation. This section explains the engines in detail.

SimulationEngine
----------------

The `SimulationEngine` is the main engine class. Upon instantiation (i.e., in the `__init__()` method), all sub-engines are created which drive the different parts if the Geant4 simulation. The sub-engines keep a reference to the `SimulationEngine` which created them.

The three main methods of the `SimulationEngine` are `SimulationEngine.run_engine()`, `SimulationEngine.initialize()` and `SimulationEngine.start_and_stop()`, where the latter two are called by the former.
The method `SimulationEngine.run_engine()` essentially takes the role of the `main.cc` in a pure Geant4 simulation. It first initializes the simulation with `SimulationEngine.initialize()` and then starts event loop with `SimulationEngine.start_and_stop()` via the `SourceEngine`.

The `SimulationEngine` uses the `G4RunManager` via a pybind11 wrapping and many Geant4 objects are created by the `G4RunManager`. In short: The `G4RunManager` is informed about the geometry, physics, and sources via its `SetUserInitialization()` method. The Geant4 initialization procedure is then triggered by `g4_RunManager.Initialize()`, just as a regular Geant4 simulation would.
For details, please consult the Geant4 user guide.

Note that there are subtleties concerning the way the `G4RunManager` works in singlethread and multithread mode which we do not cover in this guide.

Complementary to the `g4_RunManager.Initialize()`, there are expicit calls to `initialize()` methods of the sub-engines, some of them before `g4_RunManager.Initialize()` and some afterwards.

The `SimulationEngine` is implemented as what is known in python as *context manager*. This means, in can be created in a *with-clause*: `with SimulationEngine(self) as se: ...` (see `SimulationEngine._run_simulation_engine()`). What it does is that the `SimulationEngine` object only exists as long as the commands inside the *with-clause* are executed. At the end of the *with-clause*, python calls the method `SimulationEngine.__exit__()` (like an exit hook) which triggers the method `SimulationEngine.close()`. The purpose of the `close()` method is to prepare all python objects that are part of the GATE simulation for the deletion of the `G4RunManager`. In particular, it makes sure that references to those Geant4 objects which the destructor of the `G4RunManager` will delete are set to `None`. Otherwise, segmentation faults will occur. We do not go into further detail here, but it is useful to understand this background of the `close()` mechanism triggered by the *with-clause* because you, as a developer, might need to implement a `close()` method in your class or extend the `close()` in an existing class which your are enhancing (see the section on `how a class is set up in GATE <#how-a-class-in-gate-10-is-usually-set-up>`_).

It is worth noting that you have probably already come across *context managers* in python elsewhere. For example, when opening a file, you typically do `with open('my_file.txt', 'w') as f: ...`. When the *with-clause* ends, python automatically calls `f.close()`, i.e. closes the IO pipeline.

VolumeEngine
------------

*To be completed.*

PhysicsEngine
-------------

*To be completed.*

ActorEngine
-----------

*To be completed.*

SourceEngine
------------

*To be completed.*

ActionEngine
------------

*To be completed.*

OPENGATE Simulation
===================

*To be completed.*

OPENGATE elements: volumes, physic, sources, actors
===================================================

A simulation is composed of several elements: some volumes, some sources, some actors, and some physics properties. The parameters that can be defined by the user (the person that develops the simulation) are managed by a simple dict-like structure. No Geant4 objects are built until the initialization phase. This allows (relative) simplicity in the development.

UserInfo (before initialization)
--------------------------------

An 'element' can be a Volume, a Source, or an Actor. There are several element types that can be defined and used several times by the user. For example, a BoxVolume, with element_type = Volume and type_name = Box. For all elements, the user information (`user_info`) is a single structure that contains all parameters to build/manage the element (the size of a BoxVolume, the radius of a SphereVolume, the activity of a GenericSource, etc.). User info is stored in a dict-like
structure. This is performed through a `UserInfo` class inheriting from Box.

One single function is used to define the default keys of a given user info: `set_default_user_info`. This function must be defined as a static method in the class that defines the element type (BoxVolume in the previous example).

Examples:

.. code-block:: python

    vol = sim.add_volume('Type', 'name')        # -> vol is UserInfo
    sol = sim.new_solid('Type', 'name')         # -> sol is UserInfo
    src = sim.add_source('Type', 'name')        # -> src is UserInfo
    act = sim.add_actor('Type', 'name')         # -> act is UserInfo
    phys = sim.get_physics_user_info()          # -> phys is UserInfo
    filter = sim.add_filter('Type', 'name')     # -> filter is UserInfo

OPENGATE Geometry
=================

*To be completed.*

OPENGATE Physics
================

*To be completed.*

OPENGATE Source
===============

Consider the test056 and the "TemplateSource" as a starting example to create a new type of source.

Main files: `SourceManager`, `SourceBase`, `helper_sources`, all `XXXSource.py`.

- \[py\] `SourceManager`

    - Manages all sources (GateSourceManager) and all threads.
    - `run_timing_intervals`: array of start/end time for all runs
    - `sources`: dict of `SourceBase`
    - `g4_sources`: array of `GateVSource`. Needed to avoid pointer deletion on py side
    - `g4_thread_source_managers`: array of all source managers for all threads
    - `g4_master_source_manager`: master thread source manager

- \[cpp\] `GateSourceManager`

    - Manages a list of sources.
    - `fSources`: list of all managed `GateVSource` sources
    - `initialize`: set the time intervals
    - `start_main_thread`: start the simulation, only for the main thread
    - `GeneratePrimaries`: will be called by the G4 engine.

A source type is split into two parts: py and cpp. The py part inherits from `SourceBase` and manages the user info. The
cpp part inherits from `GateVSource` and shoots the particles.

- \[py\] `SourceBase`

    - Base class for all types of source (py side)
    - Used to store the user info of the source
    - Manages the start and end time of the source
    - The `create_g4_source` function must be overloaded

- \[cpp\] `GateVSource`

    - Base class for all types of source (cpp side)
    - `GeneratePrimaries`: is the main function that will be called by the source manager
    - `PrepareNextRun` and `PrepareNextTime` must be implemented. Will be called by the SourceManager to determine when this source shoots particles.

The `SourceManager` class manages 1) all sources of particles and 2) the time associated with all runs. The sources are `SourceBase` objects that manage 1) the user properties stored in `user_info` and 2) the corresponding cpp object inheriting from `GateVSource`. The latter are created in the function `build()` by the `create_g4_source()` function and stored in the `self.g4_sources` array to avoid py pointer automatic deletion.

The `GateSourceManager` inherits from G4 `G4VUserPrimaryGeneratorAction`. It manages the generation of events from all sources. The G4 engine calls the method `GeneratePrimaries` every time an event should be simulated. The current active source and time of the event is determined at this moment, the source manager chooses the next source that will shoot events according to the current simulation time. There is one GateSourceManager per thread.

All sources must inherit from `SourceBase` class. It must implement the function `create_g4_source` that will build the corresponding cpp source (that inherits from `GateVSource`). The goal of the py `SourceBase` is to manage the user options of the source and pass them to the cpp side.

OPENGATE Actors
===============

TODO --> inheritance to allow callback ; warning cost trampoline

Actors encapsulate several Geant4 concepts. They are used as a callback from the Geant4 engine to score information or modify the default behavior of particles during a simulation. An Actor combines the Geant4 `SensitiveDetector` and `Actions` callbacks within a single concept that can perform tasks each time a `Run`, `Event`, `Track` or `Step` starts or ends in a given volume. Actors are mainly used to record parameters or information of interest calculated during the simulation, but they can also be used to act on the current particle, for example to stop tracking it.

How to develop a new Actor?
---------------------------

Warning: this is a preliminary (short) documentation at an early stage of the code (July 2022). It could be outdated.

We recommend looking at an example (e.g., `GateDoseActor`). The main concept is to write a cpp class that will act during the simulation and manage all user options and parameters from the python side. Geant4 messengers are no longer used. There is a mechanism, explained below, to convert python options to cpp options. Writing a new actor (a kind of scorer) involves 4 steps.

Documentation for the documentation
===================================

The document is created with `readthedoc <https://docs.readthedocs.io/en/stable/index.html>`_. To build the html pages locally, use `make html` in the `docs/` folder of the source directory. Configuration is in the `docs/source/config.py` file. The current theme is `sphinx_pdj_theme <https://github.com/jucacrispim/sphinx_pdj_theme>`_.

Help with reStructuredText syntax:

- `quickref <https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_
- `directives <https://docutils.sourceforge.io/docs/ref/rst/directives.html>`_

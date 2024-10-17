## Helpers

Error handling. Use the following to fail with an exception and trace:

```python
import opengate as gate

gate.raise_except('There is bug')
gate.exception.fatal('This is a fatal error')
gate.exception.warning('This is a warning')
```

There are several levels: `WARNING INFO DEBUG`. The last one print more information. Logging is handled with logger in `helpers_log.py`.

## Engines
As explained [above](#gate-architecture-managers-and-engines), the Engine classes drive the actual Geant4 simulation. This section explains the engines in detail.

### SimulationEngine
The `SimulationEngine` is the main engine class. Upon instantiation (i.e., in the `__init__()` method), all sub-engines are created which drive the different parts if the Geant4 simulation. The sub-engines keep a reference to the `SimulationEngine` which created them.

The three main methods of the `SimulationEngine` are `SimulationEngine.run_engine()`, `SimulationEngine.initialize()` and `SimulationEngine.start_and_stop()`, where the latter two are called by the former.
The method `SimulationEngine.run_engine()` essentially takes the role of the `main.cc` in a pure Geant4 simulation. It first initializes the simulation with `SimulationEngine.initialize()` and then starts event loop with `SimulationEngine.start_and_stop()` via the `SourceEngine`.

The `SimulationEngine` uses the `G4RunManager` via a pybind11 wrapping and many Geant4 objects are created by the `G4RunManager`. In short: The `G4RunManager` is informed about the geometry, physics, and sources via its `SetUserInitialization()` method. The Geant4 initialization procedure is then triggered by `g4_RunManager.Initialize()`, just as a regular Geant4 simulation would.
For details, please consult the Geant4 user guide.

Note that there are subtleties concerning the way the `G4RunManager` works in singlethread and multithread mode which we do not cover in this guide.

Complementary to the `g4_RunManager.Initialize()`, there are expicit calls to `initialize()` methods of the sub-engines, some of them before `g4_RunManager.Initialize()` and some afterwards.

The `SimulationEngine` is implemented as what is known in python as *context manager*. This means, in can be created in a *with-clause*: `with SimulationEngine(self) as se: ...` (see `SimulationEngine._run_simulation_engine()`). What it does is that the `SimulationEngine` object only exists as long as the commands inside the *with-clause* are executed. At the end of the *with-clause*, python calls the method `SimulationEngine.__exit__()` (like an exit hook) which triggers the method `SimulationEngine.close()`. The purpose of the `close()` method is to prepare all python objects that are part of the GATE simulation for the deletion of the `G4RunManager`. In particular, it makes sure that references to those Geant4 objects which the destructor of the `G4RunManager` will delete are set to `None`. Otherwise, segmentation faults will occur. We do not go into further detail here, but it is useful to understand this background of the `close()` mechanism triggered by the *with-clause* because you, as a developer, might need to implement a `close()` method in your class or extend the `close()` in an existing class which your are enhancing (see the section on [how a class is set up in GATE](#how-a-class-in-gate-10-is-usually-set-up-).

It is worth noting that you have probably already come across *context managers* in python elsewhere. For example, when opening a file, you typically do `with open('my_file.txt', 'w') as f: ...`. When the *with-clause* ends, python automatically calls `f.close()`, i.e. closes the IO pipeline.

### VolumeEngine


### PhysicsEngine


### ActorEngine


### SourceEngine


### ActionEngine

[//]: # ()
[//]: # (## OPENGATE Simulation)

[//]: # ()
[//]: # (Main object:)

[//]: # ()
[//]: # (```python)

[//]: # (sim = gate.Simulation&#40;&#41;)

[//]: # (ui = sim.user_info)

[//]: # (ui.verbose_level = gate.DEBUG)

[//]: # (ui.g4_verbose = False)

[//]: # (ui.g4_verbose_level = 1)

[//]: # (ui.visu = False)

[//]: # (ui.random_engine = 'MersenneTwister')

[//]: # (ui.random_seed = 'auto')

[//]: # (```)

[//]: # ()
[//]: # (The `Simulation` class contains:)

[//]: # ()
[//]: # (- some global properties such as verbose, visualisation, multithread. All options are stored in `user_info` variable &#40;a kind of dict&#41;)

[//]: # (- some managers: volume, source, actor, physics)

[//]: # (- some G4 objects &#40;RunManager, RandomEngine etc&#41;)

[//]: # (- some variables for internal state)

[//]: # ()
[//]: # (And the following methods:)

[//]: # ()
[//]: # (- some methods for print and dump)

[//]: # (- `initialize`)

[//]: # (- `apply_g4_command`)

[//]: # (- `start`)

---
## OPENGATE elements: volumes, physic, sources, actors

A simulation is composed of several elements: some volumes, some sources, some actors and some physics properties. The parameters that can be defined by the user (the person that develop the simulation) are managed by simple dict-like structure. No Geant4 objects are build until the initialization phase. This allows (relative) simplicity in the development.

### UserInfo (before initialisation)

An 'element' can be a Volume, a Source or an Actor. There are several element type that can be defined and use several time by user. For example, a BoxVolume, with element_type = Volume and type_name = Box. For all element, the user information (`user_info`) is a single structure that contains all parameters to build/manage the element (the size of a BoxVolume, the radius of a SphereVolume, the activity of a GenericSource etc). User info are stored in a dict-like
structure. This is performed through a `UserInfo` class inheriting from Box.

One single function is used to define the default keys of a given user info : `set_default_user_info`. This function must be defined as a static method in the class that define the element type (BoxVolume in the previous example).

Examples:

```python
vol = sim.add_volume('Type', 'name')        # -> vol is UserInfo
sol = sim.new_solid('Type', 'name')         # -> sol is UserInfo
src = sim.add_source('Type', 'name')        # -> src is UserInfo
act = sim.add_actor('Type', 'name')         # -> act is UserInfo
phys = sim.get_physics_user_info()          # -> phys is UserInfo
filter = sim.add_filter('Type', 'name')     # -> filter is UserInfo
```

---
## OPENGATE Geometry

todo

VolumeManager VolumeBase SolidBuilderBase helpers_volumes Volume Material

- files: VolumeManager, MaterialDatabase, MaterialBuilder
- sim.add_material_database
- volume_manager.add_material_database
- create one MaterialDatabase for each added database file
- MaterialDatabase read the file and build a dict structure
- during volume construction, when a material is needed, call the method FindOrBuildMaterial that will either retrieve a pointer to a G4Material if it has already be build, or use the dict to build it.

---
## OPENGATE Physics

todo

---
## OPENGATE Source

Consider the test056 and the "TemplateSource" as a starting example to create a new type of source.


Main files: `SourceManager`, `SourceBase`,\`helper_sources\`, all `XXXSource.py`.

- \[py\] `SourceManager`

    - Manages all sources (GateSourceManager) and all threads.
    - `run_timing_intervals` : array of start/end time for all runs
    - `sources` : dict of `SourceBase`
    - `g4_sources` : array of `GateVSource`. Needed to avoid pointer deletion on py side
    - `g4_thread_source_managers` : array of all source managers for all threads
    - `g4_master_source_manager` : master thread source manager

- \[cpp\] `GateSourceManager`

    - Manages a list of sources.
    - `fSources` : list of all managed `GateVSource` sources
    - `initialize` : set the time intervals
    - `start_main_thread` : start the simulation, only for the main thread
    - `GeneratePrimaries` : will be called by the G4 engine.

A source type is split into two parts: py and cpp. The py part inherits from `SourceBase` and manages the user info. The
cpp part inherits from `GateVSource` and shoot the particles.

- \[py\] `SourceBase`

    - Base class for all types of source (py side)
    - Used to store the user info of the source
    - Manages the start and end time of the source
    - The `create_g4_source` function must be overloaded

- \[cpp\] `GateVSource`

    - Base class for all types of source (cpp side)
    - `GeneratePrimaries`: is the main function that will be called by the source manager
    - `PrepareNextRun` and `PrepareNextTime` must be implemented. Will be called by the SourceManager to determine when this source shoot particles.

The `SourceManager` class manages 1) all sources of particles and 2) the time associated with all runs. The sources are `SourceBase` objects that manage 1) the user properties stored in `user_info` and 2) the corresponding cpp object inheriting from `GateVSource`. The latter are created in the function `build()` by the `create_g4_source()` function and stored in the `self.g4_sources` array to avoid py pointer automatic deletion.

The `GateSourceManager` inherits from G4 `G4VUserPrimaryGeneratorAction`. It manages the generation of events from all sources. The G4 engine call the method `GeneratePrimaries` every time a event should be simulated. The current active source and time of the event is determined at this moment, the source manager choose the next source that will shoot events according to the current simulation time. There are one GateSourceManager per thread.

All sources must inherit from `SourceBase` class. It must implement the function `create_g4_source` that will build the corresponding cpp source (that inherit from `GateVSource`). The goal of the py `SourceBase` is to manage the user options of the source and pass them to the cpp side.

---
## OPENGATE Actors

TODO --> inheritance to allow callback ; warning cost trampoline

Actors encapsulate several Geant4 concepts. They are used as a callback from the Geant4 engine to score information or modify the default behavior of particles during a simulation. An Actor combines the Geant4 `SensitiveDetector`and `Actions` callbacks within a single concept that can perform tasks each time a `Run`, `Event`, `Track` or `Step`starts or ends in a given volume. Actors are mainly used to record parameters or information of interest calculated during the simulation, but they can also be used to act on the current particle, for example to stop tracking it.

### Hits collections

cpp

- GateTree: manage a list of Branch\<T>

    - map name \<-> branch
    - Get branches as double/int/vector etc
    - WriteToRoot
    - generic FillStep in all branches
    - TEMPORARY : host process EnergyWindow and TakeEnergyCentroid

- GateBranch\<T>: simple vector of T

    - FillToRoot helper

- GateVBranch: abstraction of branch

    - declare list of available branches: explicit name and type

- GateDigitizerHitsCollectionActor

    - manage a list of Tree and (later) a list of process to create trees

TODO : list of availble branches ? no command to display py VBranch static

### How to develop a new Actor ?

Warning: this is a preliminary (short) documentation at an early stage of the code (July 2022). It could be outdated.

We recommend to look at an example (e.g. `GateDoseActor` ). The main concept is to write a cpp class that will act during the simulation, and to manage all users options and parameters from the python side. Geant4 messengers are no longer used. There is a mechanism, explained below, in order to convert python options to cpp options. Writing a new actor (a kind of scorer) involves 4 steps.

#### 1 - Create a c++ class `GateMyActor`

In a file `GateMyActor.cpp`, Within the `core/opengate_core/opengate_lib/` folder. This class should inherit from `GateVActor` and implement the virtual functions that are triggered by Geant4 engine when Run, Event, Track or Step start or end. Here are the list of functions:

- `StartSimulationAction` : called when the simulation starts, only by the master thread
- `BeginOfRunAction` : called every time a Run starts (all worker threads)
- `BeginOfEventAction` : called every time an Event starts (all worker threads)
- `PreUserTrackingAction` : called every time a Track starts (all worker threads)
- `SteppingAction` : called every time a step occurs in the volume attached to the actor
- `PostUserTrackingAction` : called every time a Track ends (all worker threads)
- `EndOfEventAction`: called every time an Event ends (all worker threads)
- `EndOfRunAction`: called every time a Run ends (all worker threads)
- `EndOfSimulationWorkerAction`: called when the simulation ends, only by the workers threads
- `EndSimulationAction` : called when the simulation ends, only by the master thread

Those functions are only triggered if the actions is registered. This is done by appending the name of the actions in the `fActions` vector (see below). User options or parameters will come from the Python. It is recommended to put only the minimal set of users options in this class, stored in one single python dictionary called `user_info`. You can retrieve this dict from a parameter of the constructor of the actor, and parse it thanks to function in `GateHelpersDict.h`.

```cpp
GateMyActor::GateMyActor(py::dict &user_info) : GateVActor(user_info) {
    // Actions enabled for this actor
    fActions.insert("SteppingAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndSimulationAction");

    // Options
    fOutputFilename = DictGetStr(user_info, "output");
    fMyFlag = DictGetBool(user_info, "flag");
}
```

#### 2 - Expose this class to python side

This is done by creating a cpp file `pyGateMyActor.cpp`, look at `pyGateDoseActor.cpp` as example. This file contains one unique function (called `init_GateMyActor`) that indicates what are the member functions or variables that should be exposed to python. Most of the time, there are very few elements, or none. The constructor is however mandatory. The exposed functions could then be called from the python side.

This function must be declared in the `core/opengate_core.cpp` file (defined at the beginning and called within the main function).

#### 3 - Create a python file `MyActor.py` with the corresponding python class

This file must contain one class  `MyActor`, inheriting from 2 classes: 1) the cpp class you just wrote in the previous step, `g4.GamMyActor` and 2) the python `gate.ActorBase` class. The  `MyActor` class must implement:

- `set_default_user_info(user_info)` that will initialize all options of the user_info dictionary. All options must be indicated here.
- `__init__(self, user_info)` the constructor, that must call the two constructors of the mother classes
- `initialize` that will be called during initialization

```python
class DoseActor(g4.GateMyActor, gate.ActorBase):

    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        # required user info, default values
        user_info.output = 'default.txt'
        user_info.flag = False

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateMyActor.__init__(self, user_info.__dict__)

    def initialize(self):
        gate.ActorBase.initialize(self)

    def StartSimulationAction(self):
        g4.GateMyActor.StartSimulationAction(self)
        print('optional')

    def EndSimulationAction(self):
        g4.GateMyActor.EndSimulationAction(self)

    # etc
```

Finally, the new actor must be declared in the `opengate/actor/helpers_actor.py` file.

#### 4 - Conclusion

A new actor is defined by two interconnected classes, one in cpp, one in python. User options and parameters are stored in one single dictionary object, build from python side, and read from cpp side. If the user options is complicated, with numerous options and parameters, it is recommended to manage it from python side and only consider a unique minimal set of required options on the cpp side. Reading input and writing output are generally performed on python side.

---

## SimulationEngine




---

## Documentation for the documentation

Document is done with [readthedoc](https://docs.readthedocs.io/en/stable/index.html). To build the html pages locally, use `make html` in the `docs/` folder of the source directory. Configuration is in the `docs/source/config.py` file. The current theme is [sphinx_pdj_theme](https://github.com/jucacrispim/sphinx_pdj_theme)

Help with reStructuredText (awful) syntax.

- <https://docutils.sourceforge.io/docs/user/rst/quickref.html>
- <https://docutils.sourceforge.io/docs/ref/rst/directives.html>

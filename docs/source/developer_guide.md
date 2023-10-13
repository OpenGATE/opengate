# Developer guide

## Installation for developers

The source code is divided into two main modules, one in C++, the second in Python. The first module is used to access the Geant4 engine and for the tasks that demand speed during the run of a simulation. The second module manages user interface (the way an user create a simulation) and most tasks performed at initialization (before the run).

- `opengate_core` (C++) contains C++ Geant4 bindings and a C++ library that uses Geant4. The two components form a single Python module called `opengate_core` that can interact with Geant4 library and expose to Python functions and classes. Sources: [opengate_core](https://github.com/OpenGATE/opengate/tree/master/core)
- `opengate` (Python) is the main Python module that form the interface to the user.
  Sources: [opengate](https://github.com/OpenGATE/opengate/tree/master/opengate)

**WARNING** it is highly, highly, *highly* advised to first create a python environment, for example with [venv](https://docs.python.org/3/library/venv.html#module-venv) or [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#).

To **develop**, you need 1) to compile and create the first `opengate_core` module and 2) pip install the second (Python only) `opengate` module.

First, clone the unique repository that contains both modules:

```bash
git clone --recurse-submodules https://github.com/OpenGATE/opengate
```

Note that you need to also clone the included submodules (pybind11, all data for tests etc). If you forget the `--recurse-submodules` you can still use `git submodule update --init --recursive` after the clone.

First step: compile `opengate_core` (this is the hardest part). You need to set the path to build Geant4 and ITK libraries ; it means you need first to download and compile both [Geant4](https://geant4.web.cern.ch) and [ITK](https://itk.org).

#### STEP 1 - Geant4 and Qt

Installing QT is optional. Currently, QT visualisation is not working on all architectures.

If you wish to use QT, you must install qt5 **before** installing Geant4 so that Geant4 can find the correct qt lib. It can be done for example with conda:

```bash
  conda install qt=5
```

For **Geant4**, you need to compile with the following options:

```bash
git clone --branch v11.1.1 https://github.com/Geant4/geant4.git --depth 1
mkdir geant4.11-build
cd geant4.11-build
cmake -DCMAKE_CXX_FLAGS=-std=c++17 \
      -DGEANT4_INSTALL_DATA=ON \
      -DGEANT4_INSTALL_DATADIR=$HOME/software/geant4/data \
      -DGEANT4_USE_QT=ON \
      -DGEANT4_USE_OPENGL_X11=ON \
      -DGEANT4_BUILD_MULTITHREADED=ON \
      ../geant4
make -j 32
```

Change the QT flag (GEANT4_USE_QT) to OFF if you did not install QT.

WARNING : from June 2023, [Geant4 11.1.1](https://geant4.web.cern.ch/download/11.1.1.html) is needed.

#### STEP 2 - ITK

For **ITK**, you need to compile with the following options:

```bash
git clone --branch v5.2.1 https://github.com/InsightSoftwareConsortium/ITK.git --depth 1
mkdir build-v5.2.1
cd build-v5.2.1
cmake -DCMAKE_CXX_FLAGS=-std=c++17 \
      -DBUILD_TESTING=OFF \
      -DITK_USE_FFTWD=ON \
      -DITK_USE_FFTWF=ON \
      -DITK_USE_SYSTEM_FFTW:BOOL=ON \
      ../ITK
make -j 32
```

#### STEP 3 - `opengate_core` module (cpp bindings)

Once it is done, you can compile `opengate_core`.

```bash
pip install colored
cd <path-to-opengate>/core
export CMAKE_PREFIX_PATH=<path-to>/geant4.11-build/:<path-to>/build-v5.1.0/:${CMAKE_PREFIX_PATH}
pip install -e . -v
```

The pip install will run cmake, compile the sources and create the module. If you are curious you can have a look the compilation folder in the `build/` folder.

#### STEP 4 - `opengate` module (python)

The second part is easier : just go in the main folder and pip install:

```bash
cd <path-to-opengate>
pip install -e . -v
```

#### STEP 5 - Before running

When you want to execute some simulations on some Linux architectures, you can encounter this kind of error:

```bash
<...>/libG4particles.so: cannot allocate memory in static TLS block
```

In such a case, in the same terminal and before to run a python script, export this line:

```bash
export LD_PRELOAD=<path to libG4processes>:<path to libG4geometry>:${LD_PRELOAD}
```

Note that this is not the case on all Linux architectures, only some (we don't know why).

Then, you can run the tests with:

```bash
opengate_tests
```

**Optional**

Some tests (e.g. test034) needs [gaga-phsp](https://github.com/dsarrut/gaga-phsp) which needs [pytorch](https://pytorch.org/) that cannot really be automatically installed by the previous pip install (at least we don't know how to do). So, in order to run those tests, you will have to install both pytorch and gaga-phsp
first with:

```bash
pip install torch
pip install gaga-phsp
pip install garf
```

## How to contribute (for developers)

We are really happy if you want to propose a new feature or changes in Gate. Please contact us and share your ideas with us - this is how Gate was born and how it will keep growing!

### Propose a pull request:
1) Fork the opengate repository into your own github.
2)  Create a branch for the feature you want to contribute, starting from the current opengate master branch.
3)  Start implementing your ideas in your newly created branch (locally) and keep committing changes as you move forward.
4)  Prefer several small commits with clear comments over huge commits involving many files and changes.
5)  Push changes to your github repo. Also pull changes from the upstream/master (opengate's master branch) regularly to stayed synced.
6)  When you go to the branch in your repository on github, you will have the option to create a Pull Request (PR). Please do that - even if you are not done yet. You can mark a pull request as `draft`.
7)  We will then see your branch as PR in the opengate repository and can better understand what you are working on, and help you out if needed.
8)  Ideally, go to the opengate repository and open your own pull request. You should see a checkbox below on the right side saying "Allow edits and access to secrets by maintainers". Please tick it. In this way, we can directly commit changes into your branch - of course we'll be in touch with you.
​

More info about [Pull Requests on github](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests).


### Tests and docmentation
It is important to make sure that Gate keeps working consistently and that simulation outcome is reliable as we keep developing the code. Therefore, we have a large set of tests which are regularly run. If you propose new features or make changes to the inner workings of Gate, please create a little test simulation that goes with it. It should be imlpemented in such a way that it checks whether the feature works as expected. This might be a check of Geant4 parameters, e.g. if production cuts are set correctly, or based on simulation outcome, such as a dose maps or a particle phase space. Best is to look at the folder `tests` in the source code.


Your test will also serve other users as example on how the new feature is used.


There is a set of functions useful for tests in `opengate/tests/utility.py` which you can, e.g., import as

```python
from opengate.tests import utility
```

Finally, please write up some lines of documentation, both for the user and/or the developer.


### Code formatting
We provide a [pre-commit](https://pre-commit.com/) to enforce code format. In order to use it, you can install it with:

```bash
pip install pre-commit
# then move to the opengate folder and do:
pre-commit install
```

Do not worry, if you forget to install it - you/we will see the error during the automatic testing (Continuous Integration) in Github and can fix it then through another commit.


---
## Geant4 bindings

This repository contains C++ source code that maps some (not all!) Geant4 classes into one single Python module. It also contains additional C++ classes that extends Geant4 functionalities (also mapped to Python). At the end of the compilation process a single Python module is available, named `opengate_core` and is ready to use from the Python side.

The source files are divided into two folders: `g4_bindings` and `opengate_lib`. The first contains pure Geant4 Python bindings allow to expose in Python a (small) part of Geant4 classes and functions. The bindings are done with the [pybind11](https://github.com/pybind/pybind11) library. The second folder contains specific opengate functionalities.

### How to add a Geant4 bindings ?

If you want to expose another Geant4 class (or functions), you need to:

- Create a `pyG4MyClass.cpp`
- With a function `init_G4MyClass` (see example in the `g4_bindings` folder)
- In this function, indicate all functions/members that you want to expose.
- Declare and call this init function in the `opengate_core.cpp` file.

### Misc

- Not clear if G4RunManager should be destructed at the end of the simulation. For the moment we use `py::nodelete` to prevent deletion because seg fault after the run.

---
## Helpers

Error handling. Use the following to fail with an exception and trace:

```python
import opengate as gate

gate.raise_except('There is bug')
gate.exception.fatal('This is a fatal error')
gate.exception.warning('This is a warning')
```

There are several levels: `WARNING INFO DEBUG`. The last one print more information. Logging is handled with logger in `helpers_log.py`.

## OPENGATE Simulation

Main object:

```python
sim = gate.Simulation()
ui = sim.user_info
ui.verbose_level = gate.DEBUG
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = 'MersenneTwister'
ui.random_seed = 'auto'
```

The `Simulation` class contains:

- some global properties such as verbose, visualisation, multithread. All options are stored in `user_info` variable (a kind of dict)
- some managers: volume, source, actor, physics
- some G4 objects (RunManager, RandomEngine etc)
- some variables for internal state

And the following methods:

- some methods for print and dump
- `initialize`
- `apply_g4_command`
- `start`

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

## Notes for developers

### Pybind11 hints

Below are a list of hints (compared to boost-python).

- <https://github.com/KratosMultiphysics/Kratos/wiki/Porting-to-PyBind11---common-steps>
- bases is not any longer required. Only its template argument must remain, in the same position of what was there before.
- The noncopyable template argument should not be provided (everything is noncopyable unless specified) - if something is to be made copyable, a copy constructor should be provided to python
- return policies, see
  <https://pybind11.readthedocs.io/en/stable/advanced/functions.html>
- `return_value_policy<reference_existing_object>` --> `py::return_value_policy::reference`
- `return_internal_reference<>()` --> `py::return_value_policy::reference_internal`
- `return_value_policy<return_by_value>()` --> `py::return_value_policy::copy`
- `add_property` --> `.def_readwrite`
- Overloading methods, i.e.: `py::overload_cast<G4VUserPrimaryGeneratorAction*>(&G4RunManager::SetUserAction))`
- Pure virtual need a trampoline class <https://pybind11.readthedocs.io/en/stable/advanced/classes.html>
- Python debug: `python -q -X faulthandler`



### Geant4 seems to be frozen/sleeping - the GIL is to blame - here is why

This is taken from Issue #145 which is now closed.

So here is what happened to me: While working on a branch, I implemented an alternative binding of the G4MTRunManager. The binding includes the function G4MTRunManager::Initialize(). The naïve implementation is:

      .def("Initialize", &G4MTRunManager::Initialize)

When I tried to run a test with threads>1, Geant4 simply stopped at some point, namely when geometry and physics list were apparently set up. No error, no segfault, no further output, no CPU load, just frozen. Umpf. After a scattering cout's through the Geant4 source could, I understood the problem, and why others, like David S, had used a smarter, less naïve binding of the Initialize() function.

Here is what went wrong: G4MTRunManager::Initialize() function first calls the single thread G4RunManager::Initialize() and then does a fake run by calling BeamOn(0); The argument n–event=zero is internally interpreted as fake run and not all steps are performed as would be in a real BeamOn(). The purpose of the fake run is to set-up the worker run managers. BeamOn(0) does trigger G4RunManager::DoEventLoop() and this in turn triggers G4MTRunManager::InitializeEventLoop (the overridden version from the inherited G4MTRunManager!). At the very end, after creating and starting workers, there is a WaitForReadyWorkers(); This function contains beginOfEventLoopBarrier.Wait(GetNumberActiveThreads()); which essentially waits until all workers release locks. Specifically, it triggers a call to G4MTBarrier::Wait() which contains a while(true) loop to repeatedly check the number of locks on the shared resource, and breaks the loop when the number of locks equals the number of threads.

Now, admittedly, I do not understand every detail here, but it is clear that Geant4’s implementation relies on locks to establish whether workers are ready. So when my simulation_engine (i.e., Gate internally) called g4_RunManager.Initialize(), it ended up stuck in the while loop waiting for the locks to decrease, which never happened. Why?

This is where the so-called Global Interpreter Lock comes into play. Read this to understand the details: https://realpython.com/python-gil/, or don’t if you are smarter than I am. Essentially, at least in the CPython implementation, there is a lock (mutex) on all resources linked to the python interpreter. Historically, the GIL was a pragmatic choice to easily integrate C-extensions into python even if they were not thread-safe. What does that have to do with Gate? Well, many objects such as physics lists, are created in python, and then communicated to the Geant4 RunManager (e.g. via SetUserInitializaition). There is thus a lock on these resources, namely the GIL. The multithread mechanism in Geant4, on the other hand, does not know about the GIL and thus cannot account for this additional lock, so the lock counter never decreases sufficiently to satisfy Geant4. A way to resolve this dilemma, without hacking around in the Geant4 code, is to instruct pybind to release the Global Interpreter Lock within the scope of the call to a C++ function, such as Initialize(). One way to achieve this is to replace the naïve

```
.def("Initialize", &G4MTRunManager::Initialize)
```

by
```
      .def("Initialize",
           [](G4MTRunManager *mt) {
             py::gil_scoped_release release;
             mt->Initialize();
           })
```
The key here is the “py::gil_scoped_release release” statement. It instructs pybind to release the GIL before calling the function Initialize(). There is actually a useful passage in pybind’s doc: https://pybind11.readthedocs.io/en/stable/advanced/misc.html

I think, in the case of Gate/Geant4, it is safe to release the GIL because we know that Geant4 handles shared resources in a thread-safe way. Quite the contrary: the GIL actually breaks G4’s mechanism.

So what I learned from this: Any Geant4 function which relies on Geant4’s MT mechanism based on locks needs to be bound to python with a “py::gil_scoped_release release” statement as above. The serial version G4RunManager::Initialize() does not need this statement (and should not have it) because it does not check locks at any point.

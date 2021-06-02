        

=================
 Developer guide
=================

----------
Principles
----------


The source code is divided into two main libraries:

* `gam_g4`: contains C++ Geant4 bindings. It builds a Python module that can interact with Geant4 library. Sources: `<https://github.com/dsarrut/gam_g4>`_
* `gam`: main Python module. Sources: `<https://github.com/dsarrut/gam>`_ 

To **develop**, you need both repositories.

First, clone, compile and install `gam_g4` by setting the paths to your local Geant4 and ITK libraries, and install the module::

  cd <path-to>/gam_g4
  export CMAKE_PREFIX_PATH=<path-to>/geant4.10.06-build/:<path-to>/build-v5.1.0/:${CMAKE_PREFIX_PATH}
  pip install -e . -v

Then, clone the `gam` repository and do a local installation::

  cd <path-to>/gam
  pip install -e . -v

Using a virtual environment (via venv or conda) is *HIGHLY*, *HIGHLY*, *HIGHLY* (got it?) recommended. 


--------------------------------------
 Geant4 bindings `gam_g4`
--------------------------------------

This repository contains C++ source code that maps some (not all!) Geant4 classes into one single Python module. It also contains additional C++ classes that extends Geant4 functionalities (also mapped to Python). At the end of the compilation process a single Python module is available, named :code:`gam_g4` and is ready to use from the Python side.

The source files are divided into two folders: :code:`g4_bindings` and :code:`gam_lib`. The first contains pure Geant4 Python bindings allow to expose in Python a (small) part of Geant4 classes and functions. The bindings is done with the `pybind11 <https://github.com/pybind/pybind11>`_ library. The second folder contains specific gam functionalities. 


Pybind11 hints
::::::::::::::

Below are a list of hints (compared to boost-python).

* https://github.com/KratosMultiphysics/Kratos/wiki/Porting-to-PyBind11---common-steps

* bases is not any longer required. Only its template argument must remain, in the same position of what was there before.

* The noncopyable template argument should not be provided (everything is noncopyable unless specified) - if something is to be made copyable, a copy constructor should be provided to python
     
* return policies, see
  https://pybind11.readthedocs.io/en/stable/advanced/functions.html

* :code:`return_value_policy<reference_existing_object>` --> :code:`py::return_value_policy::reference`
 
* :code:`return_internal_reference<>()` --> :code:`py::return_value_policy::reference_internal`
      
* :code:`return_value_policy<return_by_value>()` --> :code:`py::return_value_policy::copy`
  
* :code:`add_property` --> :code:`.def_readwrite`

* Overloading methods, i.e.: :code:`py::overload_cast<G4VUserPrimaryGeneratorAction*>(&G4RunManager::SetUserAction))`

* Pure virtual need a trampoline class https://pybind11.readthedocs.io/en/stable/advanced/classes.html

* Python debug: :code:`python -q -X faulthandler`


How to add a Geant4 bindings
::::::::::::::::::::::::::::

If you want to expose another Geant4 class (or functions), you need to:

* Create a :code:`pyG4MyClass.cpp`
* With a function :code:`init_G4MyClass` (see example in the :code:`g4_bindings` folder)
* In this function, indicate all functions/members that you want to expose.
* Declare and call this init function in the :code:`gam_g4.cpp` file. 


Tests
:::::

.. warning:: FIXME do bindings tests !


Questions
:::::::::

* Not clear if G4RunManager should be destructed at the end of the simulation. For the moment we use :code:`py::nodelete` to prevent deletion because seg fault after the run. 


----------------------
GAM general principles
----------------------

FIXME 

-----------
GAM helpers
-----------

Error handling. Use the following to fail with an exception and trace::

  gam.raise_except('There is bug')
  gam.fatal('This is a fatal error')
  gam.warning('This is a warning')

There are several levels: :code:`WARNING INFO DEBUG`. The last one print more information.

Log management::

FIXME --> no! To change

   gam.log.setLevel(gam.DEBUG)

   # will be printed only if level is at least INFO
   gam.log.info('Hello World')

   # will be printed only if level is at least DEBUG
   gam.log.debug('Hello World')



--------------
GAM Simulation
--------------

Main object::

   sim = gam.Simulation()         
   ui = sim.user_info
   ui.g4_verbose = False
   ui.g4_verbose_level = 1
   ui.visu = False
   ui.random_engine = 'MersenneTwister'
   ui.random_seed = 'auto'
          
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


----------------------------------------------
GAM elements: volumes, physic, sources, actors
----------------------------------------------

A simulation is composed of several elements: some volumes, some sources, some actors and some physics properties. The parameters that can be defined by the user (the person that develop the simulation) are managed by simple dict-like structure. No Geant4 objects are build until the initialization phase. This allow (relative) simplicity in the development.


UserInfo (before initialisation)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An 'element' can be a Volume, a Source or an Actor. There are several element type that can be defined and use several time by user. For example, a BoxVolume, with element_type = Volume and type_name = Box. For all element, the user information (`user_info`) is a single structure that contains all parameters to build/manage the element (the size of a BoxVolume, the radius of a SphereVolume, the activity of a GenericSource etc). User info are stored in a dict-like structure. This is performed through a `UserInfo` class inheriting from Box.

One single function is used to defined the default keys of a given user info : `set_default_user_info`. This function must be defined as a static method in the class that define the element type (BoxVolume in the previous example).

- sim.user_info TODO 
- vol    = sim.add_volume('Type', 'name') -> vol is UserInfo
- sol    = sim.new_solid('Type', 'name')  -> sol is UserInfo
- src    = sim.add_source('Type', 'name') -> src is UserInfo
- act    = sim.add_actor('Type', 'name')  -> act is UserInfo
- phys   = sim.get_physics_user_info()    -> phys is UserInfo
- filter =  


During  initialisation
^^^^^^^^^^^^^^^^^^^^^^

After initialisation
^^^^^^^^^^^^^^^^^^^^



------------
GAM Geometry
------------

VolumeManager
VolumeBase
SolidBuilderBase
helpers_volumes

Volume



Material
- files: VolumeManager, MaterialDatabase, MaterialBuilder
- sim.add_material_database
- volume_manager.add_material_database
- create one MaterialDatabase for each added database file
- MaterialDatabase read the file and build a dict structure
- during volume construction, when a material is needed, call the method FindOrBuildMaterial that will either retrive a pointer to a G4Material if it has already be build, or use the dict to build it. 



-----------
GAM Physics
-----------

----------
GAM Source
----------


TODO --> composition py/cpp (while actor = inherit)

Main files: `SourceManager`, `SourceBase`,`helper_sources`, all `XXXSource.py`.

- [py] `SourceManager`
  - Manages all sources (GamSourceManager) and all threads.
  - `run_timing_intervals` : array of start/end time for all runs
  - `sources` : dict of `SourceBase`
  - `g4_sources` : array of `GamVSource`. Needed to avoid pointer deletion on py side
  - `g4_thread_source_managers` : array of all source managers for all threads
  - `g4_master_source_manager` : master thread source manager

- [cpp] `GamSourceManager`
  - Manages a list of sources.
  - `fSources` : list of all managed `GamVSource` sources
  - `initialize` : set the time intervals
  - `start_main_thread` : start the simulation, only for the main thread
  - `GeneratePrimaries` : will be called by the G4 engine. 

A source type is split into two parts: py and cpp. The py part inherits from `SourceBase` and manages the user info. The cpp part inherits from `GamVSource` and shoot the particles. 
  
- [py] `SourceBase`
  - Base class for all types of source (py side)
  - Used to store the user info of the source
  - Manages the start and end time of the source
  - The `create_g4_source` function must be overloaded

- [cpp] `GamVSource`
  - Base class for all types of source (cpp side)
  - `GeneratePrimaries`: is the main function that will be called by the source manager
  - `PrepareNextRun` and `PrepareNextTime` must be implemented. Will be called by the SourceManager to determine when this source shoot particles.
  

The `SourceManager` class manages 1) all sources of particles and 2) the time associated with all runs. The sources are `SourceBase` objects that manage 1) the user properties stored in `user_info` and 2) the corresponding cpp object inheriting from `GamVSource`. The latter are created in the function `build()` by the `create_g4_source()` function and stored in the `self.g4_sources` array to avoid py pointer automatic deletion. 

The `GamSourceManager` inherits from G4 `G4VUserPrimaryGeneratorAction`. It manages the generation of events from all sources. The G4 engine call the method `GeneratePrimaries` every time a event should be simulated. The current active source and time of the event is determined a this moment, the source manager choose the next source that will shoot events according to the current simulation time. There are one GamSourceManager per thread.

All sources must inherit from `SourceBase` class. It must implement the function `create_g4_source` that will build the corresponding cpp source (that inherit from `GamVSource`). The goal of the py `SourceBase` is to manage the user options of the source and pass them to the cpp side.


----------
GAM Actors
----------

FIXME check actor_info

TODO --> inheritance to allow callback ; warning cost trampoline

-------------
Documentation
-------------

Document is done with `readthedoc <https://docs.readthedocs.io/en/stable/index.html>`_. To build the html pages locally, use :code:`make html` in the :code:`docs/` folder of the source directory. Configuration is in the :code:`docs/source/config.py` file. The current theme is `sphinx_pdj_theme <https://github.com/jucacrispim/sphinx_pdj_theme>`_

Help with reStructuredText (awful) syntax.

* https://docutils.sourceforge.io/docs/user/rst/quickref.html
* https://docutils.sourceforge.io/docs/ref/rst/directives.html


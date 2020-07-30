

=================
 Developer guide
=================

----------
Principles
----------


The source code is divided into two main libraries:

* `gam_g4`: contains C++ Geant4 bindings. It builds a Python module that can interact with Geant4 library. Sources: `<https://gitlab.in2p3.fr/davidsarrut/gam_g4>`_
* `gam`: main Python module. Sources: `<https://gitlab.in2p3.fr/davidsarrut/gam>`_ 

--------------------------------------
 Geant4 bindings `gam_g4`
--------------------------------------

This repository contains C++ source code that maps some (very few!)  Geant4 classes into one single Python module. It also contains additional C++ classes that extends Geant4 functionalities (also mapped to Python). At the end of the compilation process a single Python module is available, named :code:`gam_g4` and is ready to use from the Python side.

The source files are divided into two folders: :code:`g4_bindings` and :code:`gam_bindings`. The first contains pure Geant4 Python bindings allow to expose in Python a (small) part of Geant4 classes and functions.

The bindings is done with the `pybind11 <https://github.com/pybind/pybind11>`_ library.


Compilation
:::::::::::

To compile the module, use standard cmake compilation:

.. code:: python

   mkdir build
   cd build
   make

.. warning:: FIXME -> create a Python module ?


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

Error handling. Use the following to fail with an exception and trace. 

.. code:: python
   
   gam.raise_except('There is bug')
   gam.fatal('This is a fatal error')
   gam.warning('This is a warning')


Log management. 

.. code:: python

   gam.logging_conf(True)

   # will be printed only if previous command is True
   log.info('Hello World')


Units value. Retrieve Geant4 physics units management with the following. 

.. code:: python

   cm = gam.g4_units('cm')
   MeV = gam.g4_units('MeV')          
   x = 32*cm
   energy = 150*MeV



--------------
GAM Simulation
--------------

Main object

.. code:: python

   s = gam.Simulation()
          
   # Geant4 verbose output
   s.disable_g4_verbose() # default
   s.enable_g4_verbose()

   # random engine
   s.set_random_engine("MersenneTwister") # default = 'auto'
   s.set_random_engine("MersenneTwister", 123456)
   print(s.seed)
          
Try to keep lowcase function name for python side, and CamelCase style for G4 related function and classes.
          
------------
GAM Geometry
------------

-----------
GAM Physics
-----------

-------------
Documentation
-------------

Document is done with `readthedoc <https://docs.readthedocs.io/en/stable/index.html>`_. To build the html pages locally, use :code:`make html` in the :code:`docs/` folder of the source directory. Configuration is in the :code:`docs/source/config.py` file. The current theme is `sphinx_pdj_theme <https://github.com/jucacrispim/sphinx_pdj_theme>`_

Help with reStructuredText (awful) syntax.

* https://docutils.sourceforge.io/docs/user/rst/quickref.html
* https://docutils.sourceforge.io/docs/ref/rst/directives.html




User guide
##########

**Why this new GAM_GATE project ?**

The GATE project is more than 15 years old. During this time, it evolves a lot, it now allows to perform a wide range of medical physics simulations such as various imaging systems (PET, SPECT, Compton Cameras, X-ray, etc) and dosimetry studies (external and internal radiotherapy, hadrontherapy, etc). This project led to hundreds of scientific publications, contributing to help researchers and industry.

GATE fully relies on `Geant4 <http://www.geant4.org>`_ for the Monte Carlo engine and provides 1) easy access to Geant4 functionalities, 2) additional features (e.g. variance reduction techniques) and 3) collaborative development to shared source code, avoiding reinventing the wheel. The user interface is done via so-called `macro` files (`.mac`) that contain Geant4 style macro commands that are convenient compared to direct Geant4 C++ coding. Note that other projects such as Gamos or Topas rely on similar principles.

Since the beginning of GATE, a lot of changes have happened in both fields of computer science and medical physics, with, among others, the rise of machine learning and Python language, in particular for data analysis. Also, the Geant4 project is still very active and is guaranteed to be maintained at least for the ten next years (as of 2020).

Despite its usefulness and its still very unique features (collaborative, open source, dedicated to medical physics), we think that the GATE software in itself, from a computer science programming point of view, is showing its age. More precisely, the source code has been developed during 15 years by literally hundreds of different developers. The current GitHub repository indicates around 50 unique `contributors <https://github.com/OpenGATE/Gate/blob/develop/AUTHORS>`_, but it has been setup only around 2012 and a lot of early contributors are not mentioned in this list. This diversity is the source of a lot of innovation and experiments (and fun!), but also leads to maintenance issues. Some parts of the code are "abandoned", some others are somehow duplicated. Also, the C++ language evolves tremendously during the last 15 years, with very efficient and convenient concepts such as smart pointers, lambda functions, 'auto' keyword ... that make it more robust and easier to write and maintain.

Keeping in mind the core pillars of the initial principles (community-based, open-source, medical physics oriented), we decide to start a project to propose a brand new way to perform Monte Carlo simulations in medical physics. Please, remember this is an experimental (crazy ?) attempt and we are well aware of the very long and large effort it requires to complete it. At time of writing, it is not known if it can be achieved, so we encourage users to continue using the current GATE version for their work. Audacious users may nevertheless try this new system and make feedback. Mad ones can even contribute ...

Never stop exploring !


**Goals and features**

The main goal of this project is to provide easy and flexible way to create Geant4-based Monte Carlo simulations for **medical physics**. User interface is completely renewed so that simulations are no more created from macro files but directly in Python.

Features:

 - Python as 'macro' language
 - Multithreading
 - Native ITK image management
 - Run on linux, mac(osx) and windows
 - Install with one command (`pip install gam-gate`)
 - ... (to be completed)


..
   Code philosophy
   ---------------

   - Keep simple user interface via dict object

   smallest possible API interface on cpp side
   main parameters manipulation on py side
   as close as G4 "spirit" as possible

   Why it is called GAM?


Installation
============

You only have to install the Python module via::

    pip install gam-gate

Then, you can create a simulation using the gam_gate module (see below). For **developers**, please look the developer
guide for the developer installation.

We highly recommend to create a specific python environment to 1) be sure all dependencies are handled properly
and 2) dont mix with your other Python modules. For example, you can use `conda`. Once the environment is created,
you need to activate it::

    conda create --name gam_env python=3.8
    conda activate gam_env
    pip install gam-gate

Useful helpers
=======================

Units values
------------

The Geant4 physics units can be retrieved with the following::

   cm = gam.g4_units('cm')
   MeV = gam.g4_units('MeV')
   x = 32*cm
   energy = 150*MeV

The units behave like in Geant4.



The 'Simulation' object
=======================

Any simulation starts by defining the (unique) `Simulation` object. The generic options can be set with the `user_info` data structure (a kind of dictionary), as follow::

    sim = gam.Simulation()
    ui = sim.user_info
    print(ui)
    ui.verbose_level = gam.DEBUG
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_engine = 'MersenneTwister'
    ui.random_seed = 'auto'


A simulation must contains 4 main elements that will define a complete simulation:

 - **Volumes**: all geometrical elements that compose the scene, such as phantoms, detector etc.
 - **Sources**: all sources of particles that will be created ex-nihilo. Each source may have different properties (localtion, direction, type of particles with their associated energy ,etc).
 - **Physics**: describe the properties of the physical models that will be simulated. It describes models, databases, cuts etc.
 - **Actors** : define what will be stored and output during the simulation. Typically, dose deposition or detected particles. This is the generic term for 'scorer'. Note that some `Actors` can not only store and output data, but also interact with the simulation itself.

Each four element will be described in the following sections.



------------

.. include:: ./user_guide_volumes.rst

------------

.. include:: ./user_guide_sources.rst

------------

.. include:: ./user_guide_physics.rst

------------

.. include:: ./user_guide_actors.rst



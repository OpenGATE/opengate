

User guide
==========

Why this new GAM project ?
--------------------------

The GATE project is more than 15 years old. During this time, it evolves a lot, now allowing to perform a wide range of medical physics simulations such as various imaging systems (PET, SPECT, Compton Cameras, X-ray, etc) and dosimetry studies (external and internal radiotherapy, hadrontherapy, etc). This project led to hundreds of scientific publications, contributing to help researchers and industrial.

GATE fully relies on `Geant4 <http://www.geant4.org>`_ for the Monte Carlo engine and provides 1) easy access to Geant4 functionalities, 2) additional features (e.g. variance reduction techniques) and 3) collaborative development to shared source code, avoiding reinventing the wheel. The user interface is done via so-called `macro` files (`.mac`) that contains Geant4 style macro commands that are convenient compared to direct Geant4 C++ coding. Note that others projects such as Gamos or Topas relies on similar principles.

Since the beginning of GATE, a lot of changes appends in both fields of computer science and medical physics, with, among others, the rise of machine learning and Python language, in particular for data analysis. Also, the Geant4 project is still very active and is guarantee to be maintained at least for the ten next years (as of 2020). 

Despite its usefulness and its still very unique features (collaborative, open source, dedicated to medical physics), we think that the GATE software in itself, from a computer science programming point of view, is showing is age. More precisely, the source code has been developed during 15 years by literally hundreds of different developers. The current GitHub repository indicates a bit less than 50 unique `contributors <https://github.com/OpenGATE/Gate/graphs/contributors>`_, but it has been setup only around 2012 and a lot of early contributors are not mentioned in this list. This diversity is the source of lot of innovation and experiments (and fun!), but also lead to maintenance issues. Some parts of the code are "abandoned", some others are somehow duplicated. Also, the C++ language evolves tremendously during the last 15 years, with very efficient and convenient concepts such as smart pointers, lambda functions, 'auto' keyword ... that make it more robust and easier to write and maintain.

Keeping in mind the core pillars of the initial principles (community-based, open-source, medical physics oriented), we decide to start a project to propose a brand new way to perform Monte Carlo simulations in medical physics. Please, remember this is an experimental (crazy ?) attempt and we are well aware of the very long and large effort it requires to complete it. At time of writing, it is not known if it can be achieved, so we encourage users to continue using current GATE version for their work. Audacious users may nevertheless try this new system and made feedback. Mad ones can even contribute ...

Never stop exploring ! 


GAM's goals
-----------

The main goal of this project is to provide easy and flexible way to create Geant4-based Monte Carlo  simulations for medical physics. User interface is completely renewed so that simulations are no more created from macro files but directly in Python.

Interests:
- python as 'macro' language
- with MT (?)
- native itk image management (py+cpp)
- linux + osx + win
- install with one command (pip install gam)
- time critical parts in cpp
- link with pytorch


Philosophy
----------

smallest possible API interface on cpp side
main parameters manipulation on py side
as close as G4 "spirit" as possible

          
Why it is called GAM?


Start
-----

Ideally the user will only have to install the Python module via::
  
  pip install gam
  
and start create simulation (see user guide). 
  

Simulation
----------

See examples.


Log and print information
-------------------------

Printing information about the simulation *before* the simulation start::

  gam.log.setLevel(gam.DEBUG)

There are several levels: :code:`WARNING INFO DEBUG`. The last one print more information.

In addition, more complete log text can be obtained with::

  FIXME

Printing information *during* a simulation can be done with logger that are specific to some object, such as the source logger::

  # print information every run
  gam.source_log.setLevel(gam.RUN)

  # print information every event
  gam.source_log.setLevel(gam.EVENT)



GAM Volumes
-----------

add_volume
info properties according to volume type
info on paramerter names ? help ? check

hierarchy, tree print


GAM Sources
-----------

Sources are the elements that create particles ex nihilo. The particles created from sources are called the *Event* in the Geant4 terminology, they got a *EventId* which is unique in a given *Run*.

Several sources can be managed in GAM. To add a source description to the simulation, you do::

  source1 = sim.add_source('SourceType', 'MySource')
  source1.n = 100

  Bq = gam.g4_units('Bq')
  source2 = sim.add_source('AnotherSourceType', 'MySecondSource')
  source2.activity = 10 * Bq

There are several source types, each one with different parameter. In this example, :code:`source1.n` indicates that this source will generate 10 Events. The second source manage the time and will generate 10 Events per second, so according to the simulation run timing, a different number of Events will be generated.

Information about the sources may be displayed with::

  # Print all types of source
  print(gam.info_source_types())

  # Print information about all sources
  print(gam.info_all_sources(sim))

  # Print information about all sources after initialization
  sim.initialize()
  print(gam.info_all_sources(sim))

Note that the output will be different before or after initialization. 

The `source_info` dict must contains the following keys: `type`, `name`, `start_time` and `end_time`. This is checked by the following::

  # check the validity of all sources in the simulation
  gam.assert_all_source(sim)

  # or check the validity of a single source
  gamm.assert_source(source_info)



          


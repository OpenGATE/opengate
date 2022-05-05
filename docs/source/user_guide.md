# User guide

## Why this new project ?

The GATE project is more than 15 years old. During this time, it evolves a lot, it now allows to perform a wide range of
medical physics simulations such as various imaging systems (PET, SPECT, Compton Cameras, X-ray, etc) and dosimetry
studies (external and internal radiotherapy, hadrontherapy, etc). This project led to hundreds of scientific
publications, contributing to help researchers and industry.

GATE fully relies on [Geant4](http://www.geant4.org) for the Monte Carlo engine and provides 1) easy access to Geant4
functionalities, 2) additional features (e.g. variance reduction techniques) and 3) collaborative development to shared
source code, avoiding reinventing the wheel. The user interface is done via so-called `macro` files (`.mac`) that
contain Geant4 style macro commands that are convenient compared to direct Geant4 C++ coding. Note that other projects
such as Gamos or Topas rely on similar principles.

Since the beginning of GATE, a lot of changes have happened in both fields of computer science and medical physics,
with, among others, the rise of machine learning and Python language, in particular for data analysis. Also, the Geant4
project is still very active and is guaranteed to be maintained at least for the ten next years (as of 2020).

Despite its usefulness and its still very unique features (collaborative, open source, dedicated to medical physics), we
think that the GATE software in itself, from a computer science programming point of view, is showing its age. More
precisely, the source code has been developed during 15 years by literally hundreds of different developers. The current
GitHub repository indicates around 50 unique [contributors](https://github.com/OpenGATE/Gate/blob/develop/AUTHORS), but
it has been set up only around 2012 and a lot of early contributors are not mentioned in this list. This diversity is
the source of a lot of innovation and experiments (and fun!), but also leads to maintenance issues. Some parts of the
code are "abandoned", some others are somehow duplicated. Also, the C++ language evolves tremendously during the last 15
years, with very efficient and convenient concepts such as smart pointers, lambda functions, 'auto' keyword ... that
make it more robust and easier to write and maintain.

Keeping in mind the core pillars of the initial principles (community-based, open-source, medical physics oriented), we
decide to start a project to propose a brand new way to perform Monte Carlo simulations in medical physics. Please,
remember this is an experimental (crazy ?) attempt, and we are well aware of the very long and large effort it requires
to complete it. At time of writing, it is not known if it can be achieved, so we encourage users to continue using the
current GATE version for their work. Audacious users may nevertheless try this new system and make feedback. Mad ones
can even contribute ...

Never stop exploring !

## Goals and features

The main goal of this project is to provide easy and flexible way to create Geant4-based Monte Carlo simulations for **
medical physics**. User interface is completely renewed so that simulations are no more created from macro files but
directly in Python.

Features:

- Python as 'macro' language
- Multithreading
- Native ITK image management
- Run on linux, mac and windows
- Install with one command (`pip install gam-gate`)
- ... (to be completed)

## Installation

You only have to install the Python module with:

    pip install gam-gate

Then, you can create a simulation using the gam_gate module (see below). For **developers**, please look
the [developer guide](developer_guide) for the developer installation.

```{tip} We highly recommend creating a specific python environment to 1) be sure all dependencies are handled properly and 2)
dont mix with your other Python modules. For example, you can use `conda`. Once the environment is created, you need to
activate it:
```

    conda create --name gam_env python=3.8
    conda activate gam_env
    pip install gam-gate

## Units values

The Geant4 physics units can be retrieved with the following:

```python
cm = gam.g4_units('cm')
MeV = gam.g4_units('MeV')
x = 32 * cm
energy = 150 * MeV
```

The units behave like in
Geant4 [system of units](https://geant4.web.cern.ch/sites/default/files/geant4/collaboration/working_groups/electromagnetic/gallery/units/SystemOfUnits.html)
.

## Simulation

Any simulation starts by defining the (unique) `Simulation` object. The generic options can be set with the `user_info`
data structure (a kind of dictionary), as follows:

```python
sim = gam.Simulation()
ui = sim.user_info
print(ui)
ui.verbose_level = gam.DEBUG
ui.running_verbose_level = gam.EVENT
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.visu_verbose = False
ui.random_engine = 'MersenneTwister'
ui.random_seed = 'auto'
ui.number_of_threads = 1
```

A simulation must contains 4 main elements that will define a complete simulation:

- **Volumes**: all geometrical elements that compose the scene, such as phantoms, detector etc.
- **Sources**: all sources of particles that will be created ex-nihilo. Each source may have different properties (
  localtion, direction, type of particles with their associated energy ,etc).
- **Physics**: describe the properties of the physical models that will be simulated. It describes models, databases,
  cuts etc.
- **Actors** : define what will be stored and output during the simulation. Typically, dose deposition or detected
  particles. This is the generic term for 'scorer'. Note that some `Actors` can not only store and output data, but also
  interact with the simulation itself (hence the name 'actor').

Each four elements will be described in the following sections. Once they have be defined, the simulation must be
initialized and can be started.

```python
sim.initialize()
sim.start()
```

**run and time**

```python
sim.run_timing_intervals = [[0, 0.5 * sec],
                            [0.5 * sec, 1.0 * sec],
                            # Watch out : there is (on purpose) a 'hole' in the timeline
                            [1.5 * sec, 2.5 * sec],
                            ]
```

The **verbosity**, i.e. the messages printed on the screen, are controlled via various parameters.

- `ui.verbose_level`: can be DEBUG INFO. Will display more or less messages during initialization
- `ui.running_verbose_level`: can be RUN or EVENT. Will display message during simulation run
- `ui.g4_verbose`: (bool) enable or disable the Geant4 verbose system
- `ui.g4_verbose_level`: level of the Geant4 verbose system
- `ui.visu_verbose`: enable or disable Geant4 verbose during visualisation

**Visualisation** is enabled with `ui.visu = True`. It will start a Qt interface. By default, the Geant4 visualisation commands are the ones provided in the file `gam_gate\mac\default_visu_commands.mac`. It can be changed with `self.visu_commands = gam.read_mac_file_to_commands('my_visu_commands.mac')`.

**Multithreading** is enabled with `ui.number_of_threads = 4` (larger than 1). When MT is enabled, there will one run for each thread, running in parallel. Warning, the speedup is far from optimal. First, it takes time to start a new thread. Second, if the simulation already contains several runs (for timing for example), all run will be synchronized, i.e. the master thread will wait for all threads to terminate the run before starting another one. This synchronisation takes times and may impact the speedup. 


**After the simulation ends*. Once the simulation is terminated (after the `sim.start()`), user can retrieve some actor outputs via the `sim.get_actor` function. 

------------

```{include} user_guide_volumes.md
```

------------

```{include} user_guide_sources.md
```

------------

```{include} user_guide_physics.md
```

------------

```{include} user_guide_actors.md
```



# User guide

## Why this new project ?

The GATE project is more than 15 years old. During this time, it evolves a lot, it now allows to perform a wide range of medical physics simulations such as various imaging systems (PET, SPECT, Compton Cameras, X-ray, etc) and dosimetry studies (external and internal radiotherapy, hadrontherapy, etc). This project led to hundreds of scientific publications, contributing to help researchers and industry.

GATE fully relies on [Geant4](http://www.geant4.org) for the Monte Carlo engine and provides 1) easy access to Geant4 functionalities, 2) additional features (e.g. variance reduction techniques) and 3) collaborative development to shared source code, avoiding reinventing the wheel. The user interface is done via so-called `macro` files (`.mac`) that contain Geant4 style macro commands that are convenient compared to direct Geant4 C++ coding. Note that other projects such as Gamos or Topas rely on similar principles.

Since the beginning of GATE, a lot of changes have happened in both fields of computer science and medical physics, with, among others, the rise of machine learning and Python language, in particular for data analysis. Also, the Geant4 project is still very active and is guaranteed to be maintained at least for the ten next years (as of 2020).

Despite its usefulness and its still very unique features (collaborative, open source, dedicated to medical physics), we think that the GATE software in itself, from a computer science programming point of view, is showing its age. More precisely, the source code has been developed during 15 years by literally hundreds of different developers. The current GitHub repository indicates around 70 unique [contributors](https://github.com/OpenGATE/Gate/blob/develop/AUTHORS), but it has been set up only around 2012 and a lot of early contributors are not mentioned in this list. This diversity is the source of a lot of innovation and experiments (and fun!), but also leads to maintenance issues. Some parts of the code are "abandoned", some others are somehow duplicated. Also, the C++ language evolves tremendously during the last 15 years, with very efficient and convenient concepts such as smart pointers, lambda functions, 'auto' keyword ... that make it more robust and easier to write and maintain.

Keeping in mind the core pillars of the initial principles (community-based, open-source, medical physics oriented), we decide to start a project to propose a brand new way to perform Monte Carlo simulations in medical physics. Please, remember this is an experimental (crazy ?) attempt, and we are well aware of the very long and large effort it requires to complete it. At time of writing, it is not known if it can be achieved, so we encourage users to continue using the current GATE version for their work. Audacious users may nevertheless try this new system and make feedback. Mad ones
can even contribute ...

Never stop exploring !

## Goals and features

The main goal of this project is to provide easy and flexible way to create Geant4-based Monte Carlo simulations for **medical physics**. User interface is completely renewed so that simulations are no more created from macro files but directly in Python.

Features:

- Python as 'macro' language
- Multithreading
- Native ITK image management
- Run on linux, mac (and potentially, windows)
- Install with one command (`pip install opengate`)
- ... (to be completed)

## Installation

You only have to install the Python module with:

    pip install opengate

Then, you can create a simulation using the opengate module (see below). For **developers**, please look
the [developer guide](developer_guide) for the developer installation.

```{tip} We highly recommend creating a specific python environment to 1) be sure all dependencies are handled properly and 2)
dont mix with your other Python modules. For example, you can use `conda`. Once the environment is created, you need to
activate it:
```

    conda create --name opengate_env python=3.8
    conda activate opengate_env
    pip install opengate

## Some (temporary) teaching materials

Here is a video taken on 2022-07-28 : [video](https://drive.google.com/file/d/1fdqmzhX0DFZUIO4Ds0PQZ-44obCqWb8R/view?usp=sharing). Please note, it was recored at early stage of the project, so maybe outdated.

## myBinder (experimental)

You can try by yourself the examples with myBinder. On the Github Readme, click on the myBinder shield to have the latest update. When the jupyter notebook is started, you can have access to all examples in the repository: `notebook/notebook`. Be aware, the multithreaded (MT) and visu examples do not work on that platform. Also, this is still not very usable because it is required to restart the kernel every run.

## Units values

The Geant4 physics units can be retrieved with the following:

```python
import opengate as gate
cm = gate.g4_units('cm')
MeV = gate.g4_units('MeV')
x = 32 * cm
energy = 150 * MeV
```

The units behave like in Geant4 [system of units](https://geant4.web.cern.ch/sites/default/files/geant4/collaboration/working_groups/electromagnetic/gallery/units/SystemOfUnits.html).

## Simulation

Any simulation starts by defining the (unique) `Simulation` object. The generic options can be set with the `user_info` data structure (a kind of dictionary), as follows. You can print this `user_info` data structure to see all available options with the default value `print(sim.user_info)`.

```python
sim = gate.Simulation()
ui = sim.user_info
print(ui)
ui.verbose_level = gate.DEBUG
ui.running_verbose_level = gate.EVENT
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.visu_verbose = False
ui.random_engine = 'MersenneTwister'
ui.random_seed = 'auto'
ui.number_of_threads = 1
```

A simulation must contains 4 main elements that will define a complete simulation:

- **Geometry**: all geometrical elements that compose the scene, such as phantoms, detectors, etc.
- **Sources**: all sources of particles that will be created ex-nihilo. Each source may have different properties (location, direction, type of particles with their associated energy ,etc).
- **Physics**: describe the properties of the physical models that will be simulated. It describes models, databases, cuts etc.
- **Actors** : define what will be stored and output during the simulation. Typically, dose deposition or detected particles. This is the generic term for 'scorer'. Note that some `Actors` can not only store and output data, but also interact with the simulation itself (hence the name 'actor').

Each four elements will be described in the following sections. Once they have be defined, the simulation must be initialized and can be started. The initialization corresponds to the Geant4 step needed to create the scene, gather cross-sections, etc.

```python
sim.initialize()
sim.start()
```

### Run and timing

The simulation can be split into several runs, each of them with a given time duration. Geometry can only be modified between two runs, not within one. By default, the simulation has only one run with a duration of 1 second. In the following example, we defined 3 runs, the first has a duration of half a second, the 2nd run goes from 0.5 to 1 second. The 3rd run starts latter at 1.5 second and lasts 1 second.
```python
sim.run_timing_intervals = [[0, 0.5 * sec],
                            [0.5 * sec, 1.0 * sec],
                            # Watch out : there is (on purpose) a 'hole' in the timeline
                            [1.5 * sec, 2.5 * sec],
                            ]
```

### Verbosity (for debug)

The **verbosity**, i.e. the messages printed on the screen, are controlled via various parameters.

- `ui.verbose_level`: can be DEBUG INFO. Will display more or less messages during initialization
- `ui.running_verbose_level`: can be RUN or EVENT. Will display message during simulation run
- `ui.g4_verbose`: (bool) enable or disable the Geant4 verbose system
- `ui.g4_verbose_level`: level of the Geant4 verbose system
- `ui.visu_verbose`: enable or disable Geant4 verbose during visualisation

### Visualisation

**Visualisation** is enabled with `ui.visu = True`. It will start a Qt interface. By default, the Geant4 visualisation commands are the ones provided in the file `opengate\mac\default_visu_commands.mac`. It can be changed with `self.visu_commands = gate.read_mac_file_to_commands('my_visu_commands.mac')`.

### Multithreading

**Multithreading** is enabled with `ui.number_of_threads = 4` (larger than 1). When MT is enabled, there will one run for each thread, running in parallel. Warning, the speedup is far from optimal. First, it takes time to start a new thread. Second, if the simulation already contains several runs (for timing for example), all run will be synchronized, i.e. the master thread will wait for all threads to terminate the run before starting another one. This synchronisation takes times and may impact the speedup.

### After the simulation

Once the simulation is terminated (after the `sim.start()`), user can retrieve some actor outputs via the `sim.get_actor` function.

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

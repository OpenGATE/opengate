## Introduction & installation

### Why this new project ?

The GATE project is more than 15 years old. During this time, it evolves a lot, it now allows to perform a wide range of medical physics simulations such as various imaging systems (PET, SPECT, Compton Cameras, X-ray, etc) and dosimetry studies (external and internal radiotherapy, hadrontherapy, etc). This project led to hundreds of scientific publications, contributing to help researchers and industry.

GATE fully relies on [Geant4](http://www.geant4.org) for the Monte Carlo engine and provides 1) easy access to Geant4 functionalities, 2) additional features (e.g. variance reduction techniques) and 3) collaborative development to shared source code, avoiding reinventing the wheel. The user interface is done via so-called `macro` files (`.mac`) that contain Geant4 style macro commands that are convenient compared to direct Geant4 C++ coding. Note that other projects such as Gamos or Topas rely on similar principles.

Since the beginning of GATE, a lot of changes have happened in both fields of computer science and medical physics, with, among others, the rise of machine learning and Python language, in particular for data analysis. Also, the Geant4 project is still very active and is guaranteed to be maintained at least for the ten next years (as of 2020).

Despite its usefulness and its still very unique features (collaborative, open source, dedicated to medical physics), we think that the GATE software in itself, from a computer science programming point of view, is showing its age. More precisely, the source code has been developed during 15 years by literally hundreds of different developers. The current GitHub repository indicates around 70 unique [contributors](https://github.com/OpenGATE/Gate/blob/develop/AUTHORS), but it has been set up only around 2012 and a lot of early contributors are not mentioned in this list. This diversity is the source of a lot of innovation and experiments (and fun!), but also leads to maintenance issues. Some parts of the code are "abandoned", some others are somehow duplicated. Also, the C++ language evolves tremendously during the last 15 years, with very efficient and convenient concepts such as smart pointers, lambda functions, 'auto' keyword ... that make it more robust and easier to write and maintain.

Keeping in mind the core pillars of the initial principles (community-based, open-source, medical physics oriented), we decide to start a project to propose a brand new way to perform Monte Carlo simulations in medical physics. Please, remember this is an experimental (crazy ?) attempt, and we are well aware of the very long and large effort it requires to complete it. At time of writing, it is not known if it can be achieved, so we encourage users to continue using the current GATE version for their work. Audacious users may nevertheless try this new system and make feedback. Mad ones can even contribute ...

Never stop exploring !

### Goals and features

[//]: # (The main goal of this project is to provide easy and flexible way to create Geant4-based Monte Carlo simulations for **medical physics**. User interface is completely renewed so that simulations are no more created from macro files but directly in Python.)
[//]: # (Features:)
[//]: # (- Python as 'macro' language)
[//]: # (- Multithreading)
[//]: # (- Native ITK image management)
[//]: # (- Run on linux, mac &#40;and potentially, windows&#41;)
[//]: # (- Install with one command &#40;`pip install opengate`&#41;)

The purpose of this software is to facilitate the creation of Geant4-based Monte Carlo simulations for medical physics using Python as the primary scripting language. The user interface has been redesigned to allow for direct creation of simulations in Python, rather than using macro files.

Some key features of this software include:

- Use of Python as the primary scripting language for creating simulations
- Multithreading support for efficient simulation execution
- Native integration with ITK for image management
- Compatibility with Linux, Mac, and potentially Windows operating systems
- Convenient installation via a single pip install opengate command
- ...


### Installation (for users, not developers)

You only have to install the Python module with:

    pip install opengate

Then, you can create a simulation using the opengate module (see below). For **developers**, please look the [developer guide](developer_guide) for the developer installation.

```{tip} We highly recommend creating a specific python environment to 1) be sure all dependencies are handled properly and 2) don't mix with your other Python modules. For example, you can use `conda`. Once the environment is created, you need to activate it:```

    conda create --name opengate_env python=3.10
    conda activate opengate_env
    pip install opengate


```{warning} **WARNING** This does **not** work yet on mac osx with M1 chip (we are working on it). For M1 users, you need to install gate like a developer, see : [developer guide](developer_guide). ```

Once installed, we recommend to check the installation by running the tests:

    opengate_tests

**WARNING 1** The first time a simulation is executed, the Geant4 data must be downloaded and installed. This step is automated but can take some times according to your bandwidth. Note that this is only done once. Running `opengate_info` will print some details and the path of the data.

**WARNING 2** With some linux systems (not all), you may encounter an error similar to "cannot allocate memory in static TLS block". In that case, you must add a specific path to the linker as follows:

    export LD_PRELOAD=<path to libG4processes>:<path to libG4geometry>:${LD_PRELOAD}

The libraries (libG4processes and libG4geometry) are usually found in the Geant4 folder, something like ```~/build-geant4.11.0.2/BuildProducts/lib64```.

### Additional command lines tools

There is some additional commands lines tools that can also be used. First, type ```opengate_info```, it will print some information about the current installation (Geant4 version, ITK version etc). Also, ```opengate_user_info``` is useful to print all default and possible parameters, see next section.

### Some (temporary) teaching materials

Here is a video recorded on 2022-07-28 : [video](https://drive.google.com/file/d/1fdqmzhX0DFZUIO4Ds0PQZ-44obCqWb8R/view?usp=sharing). Please note, it was recorded at early stage of the project, so maybe outdated.

### myBinder (highly experimental)

You can try by yourself the examples with myBinder. On the Github Readme, click on the myBinder shield to have the latest update. When the jupyter notebook is started, you can have access to all examples in the repository: `notebook/notebook`. Be aware, the multithreaded (MT) and visu examples do not work on that platform.

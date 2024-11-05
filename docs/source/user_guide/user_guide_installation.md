# Installation

You only have to install the Python module with, the --pre option is mandatory to have the latest release:

    pip install --pre opengate

Then, you can create a simulation using the opengate module (see below). For **developers**, please look the [developer guide](developer_guide) for the developer installation.

{tip} We highly recommend creating a specific python environment to 1) be sure all dependencies are handled properly and 2) don't mix with your other Python modules. For example, you can use `venv`. Once the environment is created, you need to activate it:

    python -m venv opengate_env
    source opengate_env/bin/activate
    pip install --pre opengate

or with `conda` environment:

    conda create --name opengate_env python=3.10
    conda activate opengate_env
    pip install --pre opengate


Maybe you need to upgrade the pip module with:

    pip install --upgrade pip

If you already installed opengate, just upgrade it with:

    pip install --upgrade --pre opengate

Once installed, we recommend to check the installation by printing GATE information and running the tests:

    opengate_info
    opengate_tests

**WARNING 1** The first time a simulation is executed, the Geant4 data must be downloaded and installed. This step is automated but can take some times according to your bandwidth. Note that this is only done once. Running `opengate_info` will print some details and the path of the data.

[//]: # (**WARNING 2** With some linux systems &#40;not all&#41;, you may encounter an error similar to "cannot allocate memory in static TLS block". In that case, you must add a specific path to the linker as follows:)

[//]: # ()
[//]: # (    export LD_PRELOAD=<path to libG4processes>:<path to libG4geometry>:${LD_PRELOAD})

[//]: # ()
[//]: # (The libraries &#40;libG4processes and libG4geometry&#41; are usually found in the Geant4 folder, something like ```~/build-geant4.11.0.2/BuildProducts/lib64```.)

### Cluster / no-OpenGL version

For some systems (clusters or older computers), the main opengate_core cannot be used due to the lack of libGL, or other visualisation librairies. For linux system, we offer a version without visualization and using older librairies. You can install it with:

    pip install --force-reinstall "opengate[novis]"

## Additional command lines tools

There is some additional commands lines tools that can also be used, see the [addons section](user_guide_addons.md).

## Teaching resources and examples

*Warning* they are only updated infrequently, you may have to adapt them to changes in the Opengate version.

- [exercices](https://gitlab.in2p3.fr/davidsarrut/gate_exercices_2) (initially developed for DQPRM, French medical physics diploma)

- [exercices](https://drive.google.com/drive/folders/1bcIS5OPLOBzhLo0NvrLJL5IxVQidNYCF) (initially developed for Opengate teaching)

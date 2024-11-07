Installation
============

You only have to install the Python module with the `--pre` option to get the latest release:

.. code-block:: bash

    pip install --pre opengate

Then, you can create a simulation using the `opengate` module (see below). For **developers**, please check the `developer guide <developer_guide>`_ for the developer installation.

.. tip:: We highly recommend creating a specific Python environment to 1) ensure all dependencies are handled properly, and 2) avoid mixing with your other Python modules. For example, you can use `venv`. Once the environment is created, activate it:

.. code-block:: bash

    python -m venv opengate_env
    source opengate_env/bin/activate
    pip install --pre opengate

or with a `conda` environment:

.. code-block:: bash

    conda create --name opengate_env python=3.10
    conda activate opengate_env
    pip install --pre opengate

You may need to upgrade the pip module with:

.. code-block:: bash

    pip install --upgrade pip

If you already have `opengate` installed, upgrade it with:

.. code-block:: bash

    pip install --upgrade --pre opengate

Once installed, we recommend checking the installation by printing GATE information and running the tests:

.. code-block:: bash

    opengate_info
    opengate_tests

**WARNING 1**: The first time a simulation is executed, Geant4 data must be downloaded and installed. This step is automated but may take some time depending on your bandwidth. Note that this is only done once. Running `opengate_info` will display details and the path of the data.

### Cluster / No-OpenGL Version

For some systems (clusters or older computers), the main `opengate_core` cannot be used due to the lack of libGL or other visualization libraries. For Linux systems, we offer a version without visualization and using older libraries. You can install it with:

.. code-block:: bash

    pip install --force-reinstall "opengate[novis]"

Note that the option `--force-reinstall` is only needed if you already installed the conventional `opengate` before.

## Additional Command Line Tools

There are additional command line tools available; see the `addons section <user_guide_addons.md>`_.

## Teaching Resources and Examples

*Warning*: These resources are only updated infrequently; you may need to adapt them to changes in the Opengate version.

- `Exercises <https://gitlab.in2p3.fr/davidsarrut/gate_exercices_2>`_ (initially developed for DQPRM, French medical physics diploma)

- `Exercises <https://drive.google.com/drive/folders/1bcIS5OPLOBzhLo0NvrLJL5IxVQidNYCF>`_ (initially developed for Opengate teaching)

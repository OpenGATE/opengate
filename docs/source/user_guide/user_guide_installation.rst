How to: Installation
====================

Install GATE with:

.. code-block:: bash

    pip install opengate

Then, you can create a simulation using the `opengate` module (see below). For **developers**, please check the `developer guide <developer_guide>`_ for the developer installation.

.. tip:: We highly recommend creating a specific Python environment to 1) ensure all dependencies are handled properly, and 2) avoid mixing with your other Python modules. For example, you can use `venv`. Once the environment is created, activate it:

.. code-block:: bash

    python -m venv opengate_env
    source opengate_env/bin/activate
    pip install --upgrade pip
    pip install opengate

or with a `conda` environment:

.. code-block:: bash

    conda create --name opengate_env python=3.12
    conda activate opengate_env
    pip install --upgrade pip
    pip install opengate

If you already have `opengate` installed, upgrade it with:

.. code-block:: bash

    pip install --upgrade opengate

Once installed, we recommend checking the installation by printing GATE information and running the tests:

.. code-block:: bash

    opengate_info
    opengate_tests

The first time a simulation is executed, Geant4 data must be downloaded and installed. This step is automated but may take some time depending on your bandwidth. Note that this is only done once. Running `opengate_info` will display details and the path of the data.

For some systems (clusters or older computers), the main `opengate_core` cannot be used due to the lack of libGL or other visualization libraries. For Linux systems, we offer a version without visualization and using older libraries. You can install it with:

.. code-block:: bash

    pip install --force-reinstall "opengate[novis]"

Note that the option `--force-reinstall` is only needed if you already installed the conventional `opengate` before.


Additional help : `"Installing Gate 10 in Ubuntu 22 in WSL2 in Windows 11 AMD64" <https://drive.google.com/file/d/1lQW2u-935ev0l5oqt5MUDaLGhYRlanVB/view?usp=drive_link>`_


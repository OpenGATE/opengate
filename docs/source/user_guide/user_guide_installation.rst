How to: Installation
====================

Install GATE with:

.. code-block:: bash

    python3 -m venv opengate_env
    source opengate_env/bin/activate
    python -m pip install --upgrade pip
    python -m pip install opengate

Then, you can create a simulation using the `opengate` module (see below). For **developers**, please check the `developer guide <../developer_guide/index.html>`_ for the developer installation.



.. tip:: We highly recommend creating a specific Python environment to 1) ensure all dependencies are handled properly, and 2) avoid mixing with your other Python modules.

If you already have `opengate` installed, upgrade it with:

.. code-block:: bash

    python -m pip install --upgrade opengate

Once installed, we recommend checking the installation by printing GATE information and running the tests:

.. code-block:: bash

    opengate_info
    opengate_tests

The first time a simulation is executed, Geant4 data must be downloaded and installed. This step is automated but may take some time depending on your bandwidth. Note that this is only done once. Running `opengate_info` will display details and the path of the data.

GATE 10 is currently tested with Python 3.10 to 3.14.
If you want to use a specific Python version, create the environment with an
explicit interpreter, for example ``python3.11 -m venv opengate_env``.

Note that ``venv`` inherits the system Python interpreter that was used when creating the virtual environment. To avoid this issue, consider using a Python package and project manager such as `uv <https://docs.astral.sh/uv/>`_ or `pixi <https://pixi.prefix.dev/latest/>`_ for creating environments because it makes it easy to manage distinct Python versions.

Version without visualization
-----------------------------

For some systems (clusters or older computers), the main `opengate_core` cannot be used due to the lack of libGL or other visualization libraries. For Linux systems, we offer a version without visualization and using older libraries. You can install it with:

.. code-block:: bash

    python3 -m venv opengate_env
    source opengate_env/bin/activate
    python -m pip install --upgrade pip
    python -m pip install "opengate[novis]"

If you already installed the conventional `opengate` package in the same
environment and want to switch to the ``novis`` variant, reinstall with:

.. code-block:: bash

    python -m pip install --force-reinstall "opengate[novis]"


Additional help : `"Installing Gate 10 in Ubuntu 22 in WSL2 in Windows 11 AMD64" <https://drive.google.com/file/d/1lQW2u-935ev0l5oqt5MUDaLGhYRlanVB/view?usp=drive_link>`_

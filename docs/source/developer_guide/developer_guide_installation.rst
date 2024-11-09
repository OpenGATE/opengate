Installation for developers
===========================

The source code is divided into two main modules, one in C++, the second
in Python. The first module is used to access the Geant4 engine and for
the tasks that demand speed during the run of a simulation. The second
module manages user interface (the way an user create a simulation) and
most tasks performed at initialization (before the run).

-  ``opengate_core`` (C++) contains C++ Geant4 bindings and a C++
   library that uses Geant4. The two components form a single Python
   module called ``opengate_core`` that can interact with Geant4 library
   and expose to Python functions and classes. Sources:
   `opengate_core <https://github.com/OpenGATE/opengate/tree/master/core>`__
-  ``opengate`` (Python) is the main Python module that form the
   interface to the user. Sources:
   `opengate <https://github.com/OpenGATE/opengate/tree/master/opengate>`__

Virtual environment
-------------------

:warning: It is highly, highly, *highly* recommended to create a python
environment prior to the installation, for example with
`venv <https://docs.python.org/3/library/venv.html#module-venv>`__.

:warning: If you use
`conda <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#>`__
instead to create your environment, be sure to instruct conda to install
python when creating your environment. You do so by adding ‘python’
after the new environment name. Optionally, you can select a specific
python version by adding ‘=3.XX’.

Example: You can create a new conda environment with Python 3.10
installed in it via:

.. code:: bash

     conda create --name opengate_env python=3.10
     conda activate opengate_env

To **develop** in GATE 10, you need 1) to compile and create the
``opengate_core`` subpackage (this is the hardest part) and 2) install
the main ``opengate`` package (Python only, fast and easy).

First, clone the unique repository that contains both packages:

.. code:: bash

   git clone --recurse-submodules https://github.com/OpenGATE/opengate

:warning: When you update, the data for the tests must also be updated,
use : ``git submodule update --init --recursive``. This also update the
included subpackages (pybind11, etc).

The subpackage ``opengate_core`` depends on the ITK and Geant4
libraries. Therefore, you first need to download and compile both
`Geant4 <https://geant4.web.cern.ch>`__ and `ITK <https://itk.org>`__.
Note: In the user install, this step is not necessary because Geant4 and
ITK are shipped pre-compiled via pip.

STEP 1 - Geant4 and Qt
----------------------

:warning: When using conda, be sure to activate your environment before
compiling Geant4. The reason is that conda comes with its own compiler
and you will likely have mismatched libraries, e.g. lib c++, if not all
installation steps involving compilaton are performed in the same conda
environment.

Installing QT is optional. Currently, QT visualisation is not working on
all architectures.

If you wish to use QT, you must install qt5 **before** installing Geant4
so that Geant4 can find the correct qt lib. It can be done for example
with conda:

.. code:: bash

     conda install qt=5

For **Geant4**, you need to compile with the following options:

.. code:: bash

   git clone --branch v11.2.1 https://github.com/Geant4/geant4.git --depth 1
   mkdir geant4.11-build
   cd geant4.11-build
   cmake -DCMAKE_CXX_FLAGS=-std=c++17 \
         -DGEANT4_INSTALL_DATA=ON \
         -DGEANT4_INSTALL_DATADIR=$HOME/software/geant4/data \
         -DGEANT4_USE_QT=ON \
         -DGEANT4_USE_OPENGL_X11=ON \
         -DGEANT4_BUILD_MULTITHREADED=ON \
         ../geant4
   make -j 32

Change the QT flag (GEANT4_USE_QT) to OFF if you did not install QT.

WARNING : since June 2024, `Geant4
11.2.1 <https://geant4.web.cern.ch/download/11.2.1.html>`__ is needed.

STEP 2 - ITK
------------

**WARNING** When using conda, be sure to activate your environment
before compiling Geant4. The reason is that conda comes with its own
compiler and you will likely have mismatched libraries, e.g. lib c++, if
not all installation steps involving compilaton are performed in the
same conda environment.

For **ITK**, you need to compile with the following options:

.. code:: bash

   git clone --branch v5.2.1 https://github.com/InsightSoftwareConsortium/ITK.git --depth 1
   mkdir itk-build
   cd itk-build
   cmake -DCMAKE_CXX_FLAGS=-std=c++17 \
         -DBUILD_TESTING=OFF \
         -DITK_USE_FFTWD=ON \
         -DITK_USE_FFTWF=ON \
         -DITK_USE_SYSTEM_FFTW:BOOL=ON \
         ../ITK
   make -j 32

STEP 3 - ``opengate_core`` module (cpp bindings)
------------------------------------------------

Once it is done, you can compile ``opengate_core``.

.. code:: bash

   pip install colored
   cd <path-to-opengate>/core
   export CMAKE_PREFIX_PATH=<path-to>/geant4.11-build/:<path-to>/itk-build/:${CMAKE_PREFIX_PATH}
   pip install -e . -v

The pip install will run cmake, compile the sources and create the
module. If you are curious you can have a look the compilation folder in
the ``build/`` folder.

STEP 4 - ``opengate`` module (python)
-------------------------------------

The second part is easier : just go in the main folder and pip install:

.. code:: bash

   cd <path-to-opengate>
   pip install -e . -v

STEP 5 - Before running
-----------------------

When you want to execute some simulations on some Linux architectures,
you can encounter this kind of error:

.. code:: bash

   <...>/libG4particles.so: cannot allocate memory in static TLS block

In such a case, in the same terminal and before to run a python script,
export this line:

.. code:: bash

   export LD_PRELOAD=<path to libG4processes>:<path to libG4geometry>:${LD_PRELOAD}

Note that this is not the case on all Linux architectures, only some (we
don’t know why).

Then, you can run the tests with:

.. code:: bash

   opengate_tests

**Optional**

Some tests (e.g. test034) needs
`gaga-phsp <https://github.com/dsarrut/gaga-phsp>`__ which needs
`pytorch <https://pytorch.org/>`__ that cannot really be automatically
installed by the previous pip install (at least we don’t know how to
do). So, in order to run those tests, you will have to install both
pytorch and gaga-phsp first with:

.. code:: bash

   pip install torch
   pip install gaga-phsp
   pip install garf

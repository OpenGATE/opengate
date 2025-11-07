![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/OpenGATE/opengate?logo=github)
[![Read the Docs](https://img.shields.io/readthedocs/opengate-python/master?logo=read-the-docs&style=plastic)](https://opengate-python.readthedocs.io/)
[![CI](https://github.com/OpenGATE/opengate/actions/workflows/main.yml/badge.svg)](https://github.com/OpenGATE/opengate/actions/workflows/main.yml)
[![cirrus CI](https://api.cirrus-ci.com/github/OpenGATE/opengate.svg)](https://cirrus-ci.com/github/OpenGATE/opengate)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/OpenGATE/opengate/master.svg)](https://results.pre-commit.ci/latest/github/OpenGATE/opengate/master)

## This is GATE 10

GATE is an open-source Monte Carlo simulation platform designed for modeling and simulating medical imaging systems, radiotherapy, and radiation dosimetry. It extends Geant4 with features tailored for time-dependent simulations, imaging physics, and therapy modeling. Widely used in **medical physics** research, GATE supports advanced applications such as PET, SPECT, CT, internal and external beam radiotherapy. GATE fosters collaboration through its active **open-source community**, enabling continuous development and shared innovation.

GATE 10 introduces a Python-based interface, replacing the macro scripting of GATE 9.x, offering improved flexibility, readability, and integration with modern scientific workflows. Read our [motivation](https://opengate-python.readthedocs.io/en/master/user_guide/user_guide_intro.html).

- Documentation: see the [User Guide](https://opengate-python.readthedocs.io/en/master/user_guide/index.html).
- This current version uses [Geant4 11.3.2](https://geant4.web.cern.ch).
- Compatible with Python 3.9, 3.10, 3.11, 3.12. (**Not python 3.13 yet**)
- **Warning**: on Windows, the multithreading and Qt visualization are not (yet) available.

### How to install (short version)

First, create a python environment:

```
python -m venv opengate_env
source opengate_env/bin/activate
pip install --upgrade pip
```

Then install the package opengate. The associated package ```opengate_core``` is automatically downloaded. ```opengate_core``` installs Geant4 librairies.

```
pip install opengate
```

If you already installed the packages and want to upgrade to the latest version:

```
pip install --upgrade opengate
```

Once installed, you can run all tests:

````
opengate_tests
````

**WARNING (1)** The first time you run this command, the geant4 data and the test data will be downloaded. If the download fails (on some systems), try to add the following command before running opengate_tests:

````
export GIT_SSL_NO_VERIFY=1
````

All tests are in the folder [here](https://github.com/OpenGATE/opengate/tree/master/opengate/tests/src). The test data (binary files) are stored as a git submodule here: https://gitlab.in2p3.fr/opengamgate/gam_tests_data.

**WARNING (2)** Some tests (e.g. test034) needs [gaga-phsp](https://github.com/dsarrut/gaga-phsp) which needs [pytorch](https://pytorch.org/) that cannot really be automatically installed by the previous pip install (at least we don't know how to do). So, in order to run those tests, you will have to install both PyTorch and gaga-phsp first with:

````
pip install torch
pip install gaga-phsp
````

The test history can be visualized here: https://opengate.github.io/opengate_tests_results

### How to install (long version, for developers)

See the [developer guide](https://opengate-python.readthedocs.io/en/master/developer_guide/index.html#installation-for-developers)


## Included third party C++ libraries

- https://github.com/pybind/pybind11
- https://github.com/fmtlib/fmt
- https://github.com/p-ranav/indicators

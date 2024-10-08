![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/OpenGATE/opengate?logo=github)
[![Read the Docs](https://img.shields.io/readthedocs/opengate-python?logo=read-the-docs&style=plastic)](https://opengate-python.readthedocs.io/)
[![CI](https://github.com/OpenGATE/opengate/actions/workflows/main.yml/badge.svg)](https://github.com/OpenGATE/opengate/actions/workflows/main.yml)
[![cirrus CI](https://api.cirrus-ci.com/github/OpenGATE/opengate.svg)](https://cirrus-ci.com/github/OpenGATE/opengate)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/OpenGATE/opengate/master.svg)](https://results.pre-commit.ci/latest/github/OpenGATE/opengate/master)

## This is GATE10 **beta** version. The first non-beta release will be officially announced ~in the summer~ autumn 2024.

See the [User Guide](https://opengate-python.readthedocs.io/en/latest/user_guide.html). The current version uses [Geant4 11.2.1](https://geant4.web.cern.ch).


### How to install (short version)

*Compatible with Python 3.9, 3.10, 3.11, 3.12. On Windows multithreading, Qt visualization and the "spawn new subprocess" are not (yet) available.*

First, create an environment (not mandatory but highly advised)

```
python -m venv opengate_env
source opengate_env/bin/activate
```

or you can use the conda environment.

```
conda create --name opengate_env python=3.9
conda activate opengate_env
```

Then install the package opengate. The package ```opengate_core``` is automatically downloaded. ```opengate_core``` installs Geant4 librairies.
```
pip install --upgrade pip
pip install --pre opengate
```

If you already installed the packages and want to upgrade to the latest version:

```
pip install --upgrade --pre opengate
```

Once installed, you can run all tests:
````
opengate_tests
````

**WARNING** The first time you run this command, the geant4 data and the test data will be downloaded. If the download fails (on some systems), try to add the following command before running opengate_tests:
````
export GIT_SSL_NO_VERIFY=1
````

All tests are in the folder [here](https://github.com/OpenGATE/opengate/tree/master/opengate/tests/src). The test data (binary files) are stored, for technical reasons, in this git: https://gitlab.in2p3.fr/opengamgate/gam_tests_data (which is stored as a git submodule).

**WARNING** Some tests (e.g. test034) needs [gaga-phsp](https://github.com/dsarrut/gaga-phsp) which needs [pytorch](https://pytorch.org/) that cannot really be automatically installed by the previous pip install (at least we don't know how to do). So, in order to run those tests, you will have to install both PyTorch and gaga-phsp first with
````
pip install torch
pip install gaga-phsp
````

The documentation is here: https://opengate-python.readthedocs.io/en/latest/user_guide.html

The test history can be visualized here: https://opengate.github.io/opengate_tests_results/

### How to install (long version, for developers)

See the documentation: https://opengate-python.readthedocs.io/en/latest/developer_guide.html#installation-for-developers


## Included third party C++ libraries
- https://github.com/pybind/pybind11
- https://github.com/fmtlib/fmt
- https://github.com/p-ranav/indicators

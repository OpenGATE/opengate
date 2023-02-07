![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/OpenGATE/opengate?logo=github)
[![CI](https://github.com/OpenGATE/opengate/actions/workflows/main.yml/badge.svg)](https://github.com/OpenGATE/opengate/actions/workflows/main.yml)
[![cirrus CI](https://api.cirrus-ci.com/github/OpenGATE/opengate.svg)](https://cirrus-ci.com/github/OpenGATE/opengate)
[![Read the Docs](https://img.shields.io/readthedocs/opengate-python?logo=read-the-docs&style=plastic)](https://opengate-python.readthedocs.io/)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/OpenGATE/opengate/master.svg)](https://results.pre-commit.ci/latest/github/OpenGATE/opengate/master)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/OpenGATE/gam-gate/c65a0d55c616748454f066470aa836331eb107ac)

This is the future GATE version 10. First release is expected 1S 2023.

# How to install (short version)

First create an environment (not mandatory but highly advised)

```
conda create --name opengate_env python=3.9
conda activate opengate_env
```

**Warning** not available for python 3.11 yet.

Then install the package opengate. The package opengate_core is automatically downloaded.
```
pip install opengate
```

If you already installed the packages and want to upgrade to last version:

```
pip install opengate -U
```

Once installed, you can run all tests:
````
opengate_tests
````

All tests are in the folder [here](https://github.com/OpenGATE/opengate/tree/master/opengate/tests/src). Some data (binary files) are stored, for technical reasons, in this git: https://gitlab.in2p3.fr/opengate/tests_data (which is stored as a git submodule).

**WARNING** some tests (e.g. test034) needs [gaga-phsp](https://github.com/dsarrut/gaga-phsp) which needs [pytorch](https://pytorch.org/) that cannot really be automatically installed by the previous pip install (at least we dont know how to do). So, in order to run those tests, you will have to install both pytorch and gaga-phsp first with
````
pip install torch
pip install gaga-phsp
````

The documentation is here: https://opengate-python.readthedocs.io/en/latest/user_guide.html

# How to install (long version, for developers)

See the documentation : https://opengate-python.readthedocs.io/en/latest/developer_guide.html#installation-for-developers

![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/OpenGATE/gam-gate?logo=github)
[![CI](https://github.com/OpenGATE/gam-gate/actions/workflows/main.yml/badge.svg)](https://github.com/OpenGATE/gam-gate/actions/workflows/main.yml)
[![Read the Docs](https://img.shields.io/readthedocs/gam-gate?logo=read-the-docs&style=plastic)](https://gam-gate.readthedocs.io/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/OpenGATE/gam-gate/mybinder)

This **experiment** is a **work in progress**. Even the name (gam-gate) is temporary and will be changed. 

# How to install (short version)

First create an environment (not mandatory but highly advised)

```
conda create --name gam_env python=3.8
conda activate gam_env
```

**Warning** not available for python 3.10 yet. 

Then install the package gam-gate. The package gam-g4 is automatically downloaded.
```
pip install gam-gate
```

If you already installed the packages and want to upgrade to last version: 

```
pip install gam-gate -U
```

Once installed, you can run all tests: 
````
gam_gate_tests
````

All tests are in the folder [here](https://github.com/OpenGATE/gam-gate/tree/master/gam_tests/src). Some data (binary files) are stored, for technical reasons, in this git: https://gitlab.in2p3.fr/opengamgate/gam_tests_data (which is stored as a git submodule).

**WARNING** some tests (e.g. test034) needs [gaga-phsp](https://github.com/dsarrut/gaga-phsp) which needs [pytorch](https://pytorch.org/) that cannot really be automatically installed by the previous pip install (at least we dont know how to do). So, in order to run those tests, you will have to install both pytorch and gaga-phsp first with
````
pip install torch
pip install gaga-phsp
````


# How to install (long version, for developers)

See the documentation : https://gam-gate.readthedocs.io/en/latest/developer_guide.html#installation-for-developers



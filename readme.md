
# Highly experimental

Folder ```py_geant4``` contains tentative python wrapping of Geant4

Folder ```gam``` contains tentative python module Gate-like simulation.

Folder ```tests``` contains example and test (will be removed). 


# Geant4 c++/python wrapping

Use pybind11 that must be installed, see https://github.com/pybind/pybind11

Build the Geant4 wrapping with:

```
mkdir build_py_geant4
cd build_py_geant4
ccmake <path_to>/py_geant4
make 
```

Use flag: ```pybind11_DIR <wpath_to>/pybind11-install/share/cmake/pybind11```

Use flag: ```Geant4_DIR <path_to>/geant4.10.06-mt-install/lib/Geant4-10.6.0```

# GAM python module

TODO 

# Tests

To run the py script, you need to set the paths to ```py_geant4``` module and ```gam``` module, and source the geant4 env script. 

```
export PYTHONPATH=<path_to>/build_py_geant4:${PYTHONPATH}
pushd <path_to>/geant4.10.06-mt-install/bin
source geant4.sh
popd
```


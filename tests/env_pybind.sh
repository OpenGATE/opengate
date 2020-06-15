

export PYTHONPATH=${HOME}/src/gate2/g4_pybind11_build:${PYTHONPATH}
export PYTHONPATH=${HOME}/src/gate2/gam/gam:${PYTHONPATH}

pushd ${HOME}/src/geant4/geant4.10.06-install/bin
source ./geant4.sh
popd



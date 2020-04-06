

export PYTHONPATH=${HOME}/src/gate2/build-pyg4:${PYTHONPATH}
export PYTHONPATH=${HOME}/src/gate2/gam/gam:${PYTHONPATH}
pushd ${HOME}/src/geant4/geant4.10.06-mt-install/bin
source ./geant4.sh
popd



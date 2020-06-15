

pushd ${HOME}/src/geant4/geant4.10.06-install/bin
source ./geant4.sh
popd

export PYTHONPATH=${HOME}/src/geant4/geant4.10.06-g4py-install/lib/Geant4:${PYTHONPATH}
export PYTHONPATH=${HOME}/src/gate2/gam/:${PYTHONPATH}


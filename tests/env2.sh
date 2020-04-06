

export G4PY=${HOME}/src/geant4/geant4.10.06/environments/g4py

export PYTHONPATH=${G4PY}/lib:${G4PY}/lib64:${PYTHONPATH}
export PYTHONPATH=${HOME}/src/gate2/gam/gam:${PYTHONPATH}

pushd ${HOME}/src/geant4/geant4.10.06-mt-install/bin
source ./geant4.sh
popd



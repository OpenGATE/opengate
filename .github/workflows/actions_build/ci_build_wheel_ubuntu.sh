#!/bin/bash
set -e

source $GITHUB_WORKSPACE/env_dump.txt
if [ ${MATRIX_PYTHON_VERSION} == "3.10" ]; then
  export PYTHONFOLDER="cp310-cp310"
elif [ ${MATRIX_PYTHON_VERSION} == "3.11" ]; then
  export PYTHONFOLDER="cp311-cp311"
elif [ ${MATRIX_PYTHON_VERSION} == "3.12" ]; then
  export PYTHONFOLDER="cp312-cp312"
elif [ ${MATRIX_PYTHON_VERSION} == "3.13" ]; then
  export PYTHONFOLDER="cp313-cp313"
fi
mkdir -p $HOME/software
if [ ${MATRIX_OS} == "ubuntu-24.04-arm" ]; then
  export ARMDOCKER="_arm64"
fi
docker run --rm -e "PYTHONFOLDER=${PYTHONFOLDER}" -v $GITHUB_WORKSPACE:/home tbaudier/opengate_core:${GEANT4_VERSION}$ARMDOCKER /home/.github/workflows/createWheelLinux.sh
ls wheelhouse
rm -rf dist
mv wheelhouse dist
sudo chown -R runner:docker dist
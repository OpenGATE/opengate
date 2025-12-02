#!/bin/bash
set -e

source $GITHUB_WORKSPACE/env_dump.txt
source $CONDA/Scripts/activate opengate_core
conda info
conda install cmake==3.31.2
cmake --version
conda list
which python
python --version
export PATH="/usr/local/miniconda/envs/opengate_core/bin/:$PATH"
pip install wheel wget colored
pip install cibuildwheel==2.21.1
which pip
mkdir -p $HOME/software
if [ "${MATRIX_CACHE}" != 'true' ]; then
    cd $HOME/software
    mkdir geant4
    cd geant4
    mkdir src bin data
    git clone --branch $GEANT4_VERSION https://github.com/Geant4/geant4.git --depth 1 src
    cd bin
    cmake -DGEANT4_INSTALL_DATA=ON \
          -DGEANT4_INSTALL_DATADIR=$HOME/software/geant4/data \
          -DGEANT4_BUILD_MULTITHREADED=ON \
          ../src
    cmake --build . --config Release
    cd $HOME/software
    mkdir itk
    cd itk
    mkdir src bin
    git clone --branch $ITK_VERSION https://github.com/InsightSoftwareConsortium/ITK.git --depth 1 src
    cd bin
    cmake -DCMAKE_CXX_FLAGS=-std=c++17 \
          -DBUILD_TESTING=OFF \
          ../src
    cmake --build . --config Release
fi
cd $GITHUB_WORKSPACE
source $HOME/software/geant4/bin/geant4make.sh
export CMAKE_PREFIX_PATH=$HOME/software/geant4/bin:$HOME/software/itk/bin/:${CMAKE_PREFIX_PATH}
cd core
if [[ ${MATRIX_PYTHON_VERSION} == "3.10" ]]; then
  export CIBW_BUILD="cp310-win_amd64"
elif [[ ${MATRIX_PYTHON_VERSION} == "3.11" ]]; then
  export CIBW_BUILD="cp311-win_amd64"
elif [[ ${MATRIX_PYTHON_VERSION} == "3.12" ]]; then
  export CIBW_BUILD="cp312-win_amd64"
elif [[ ${MATRIX_PYTHON_VERSION} == "3.13" ]]; then
  export CIBW_BUILD="cp313-win_amd64"
fi
find $HOME/software/geant4/bin/ -iname "*.dll"
ls $HOME/software/geant4/bin/BuildProducts/Release/bin
ls $HOME/software/geant4/bin/BuildProducts/Release/lib/
export CIBW_BEFORE_BUILD="python -m pip install colored"
python -m cibuildwheel --output-dir dist
cd ..
mkdir core/dist2
pip install pefile machomachomangler
ls core/dist
python $GITHUB_WORKSPACE\\.github\\workflows\\delocateWindows.py core\\dist -w core\\dist2 -d C:\\Users\\runneradmin\\software\\geant4\\bin\\BuildProducts\\Release\\bin
mv core/dist2 dist
#!/bin/bash
set -e

source $GITHUB_WORKSPACE/env_dump.txt
brew install --force --verbose --overwrite \
             ccache \
             fftw \
             libomp \
             xquartz \
             xerces-c || true
brew uninstall --ignore-dependencies libxext
brew uninstall --ignore-dependencies libx11
export LDFLAGS="-L/usr/local/opt/llvm/lib"
export CPPFLAGS="-I/usr/local/opt/llvm/include -fopenmp"
conda info
conda list
export PATH="/usr/local/miniconda/envs/opengate_core/bin/:$PATH"
pip install wget colored
# install cibuildwheel
if [[ ${MATRIX_PYTHON_VERSION} == "3.10" ]]; then
    pip install cibuildwheel[uv]==2.23.4
else
    pip install cibuildwheel[uv]==3.4.0
fi
if [[ ${MATRIX_OS} == "macos-15-intel" ]]; then
    conda install conda-forge::qt6-main conda-forge::qt6-3d
else
    brew install qt
fi
mkdir -p $HOME/software
if [ "${MATRIX_CACHE}" != 'true' ]; then
    cd $HOME/software
    mkdir geant4
    cd geant4
    mkdir src bin data
    git clone --branch $GEANT4_VERSION https://github.com/Geant4/geant4.git --depth 1 src
    cd bin
    cmake -DCMAKE_CXX_FLAGS=-std=c++17 \
          -DGEANT4_INSTALL_DATA=OFF \
          -DGEANT4_INSTALL_DATADIR=$HOME/software/geant4/data \
          -DGEANT4_USE_QT=ON \
          -DGEANT4_USE_OPENGL_X11=OFF \
          -DGEANT4_USE_QT_QT6=ON \
          -DGEANT4_USE_SYSTEM_EXPAT=OFF \
          -DGEANT4_BUILD_MULTITHREADED=ON \
          -DGEANT4_USE_GDML=ON \
          ../src
    make -j4
    cd $HOME/software
    mkdir itk
    cd itk
    mkdir src bin
    git clone --branch $ITK_VERSION https://github.com/InsightSoftwareConsortium/ITK.git --depth 1 src
    cd bin
    cmake -DCMAKE_CXX_FLAGS=-std=c++17 \
          -DBUILD_TESTING=OFF \
          -DITK_USE_FFTWD=ON \
          -DITK_USE_FFTWF=ON \
          -DITK_USE_SYSTEM_FFTW:BOOL=ON \
          ../src
    make -j4
fi
cd $GITHUB_WORKSPACE
source $HOME/software/geant4/bin/geant4make.sh
export CMAKE_PREFIX_PATH=$HOME/software/geant4/bin:$HOME/software/itk/bin/:${CMAKE_PREFIX_PATH}
cd core
mkdir opengate_core/plugins
if [[ ${MATRIX_OS} == "macos-15-intel" ]]; then
    cp -r /Users/runner/miniconda3/envs/opengate_core/lib/qt6/plugins/platforms/* opengate_core/plugins/
    cp -r /Users/runner/miniconda3/envs/opengate_core/lib/qt6/plugins/imageformats opengate_core/plugins/
else
    cp -r /opt/homebrew/share/qt/plugins/platforms/* opengate_core/plugins/
    cp -r /opt/homebrew/share/qt/plugins/imageformats/* opengate_core/plugins/
fi
export CIBW_BUILD_FRONTEND="build[uv]"
export CIBW_PLATFORM="macos"
export CIBW_SKIP="*t*"
export MACOSX_DEPLOYMENT_TARGET=15.0
export CIBW_BEFORE_BUILD="uv pip install colored"

if [[ ${MATRIX_OS} == "macos-15-intel" ]]; then
    export DYLD_LIBRARY_PATH=$HOME/software/geant4/bin/BuildProducts/lib:/Users/runner/miniconda3/envs/opengate_core/lib/qt6/plugins/platforms:/opt/X11/lib/:$DYLD_LIBRARY_PATH:/Users/runner/miniconda3/envs/opengate_core/lib
    export CIBW_ARCHS_MACOS="x86_64"
else
    export DYLD_LIBRARY_PATH=$HOME/software/geant4/bin/BuildProducts/lib:/opt/homebrew/share/qt/plugins/platforms/:/opt/X11/lib/:$DYLD_LIBRARY_PATH:/opt/homebrew/lib
    export CIBW_ARCHS_MACOS="arm64"
    python -c "import os,delocate; print(os.path.join(os.path.dirname(delocate.__file__), 'tools.py'));quit()" | xargs -I{} sed -i."" "s/first, /input.pop('i386',None); first, /g" {}
fi
if [[ ${MATRIX_PYTHON_VERSION} == "3.10" ]]; then
  export CIBW_BUILD="cp310-*"
elif [[ ${MATRIX_PYTHON_VERSION} == "3.11" ]]; then
  export CIBW_BUILD="cp311-*"
elif [[ ${MATRIX_PYTHON_VERSION} == "3.12" ]]; then
  export CIBW_BUILD="cp312-*"
elif [[ ${MATRIX_PYTHON_VERSION} == "3.13" ]]; then
  export CIBW_BUILD="cp313-*"
elif [[ ${MATRIX_PYTHON_VERSION} == "3.14" ]]; then
  export CIBW_BUILD="cp314-*"
fi

python -m cibuildwheel --output-dir dist
cd dist
if [[ ${MATRIX_OS} == "macos-15-intel" ]]; then
    find . -name '*whl' -exec bash -c ' mv $0 ${0/macosx_15_0/macosx_10_9}' {} \;
fi
cd ../..
mv core/dist .
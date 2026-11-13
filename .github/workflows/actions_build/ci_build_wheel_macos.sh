#!/bin/bash
set -e

source $GITHUB_WORKSPACE/env_dump.txt

brew install --force --verbose --overwrite \
            ccache \
            fftw \
            libomp \
            xerces-c || true

brew uninstall --ignore-dependencies libxext
brew uninstall --ignore-dependencies libx11

conda info
conda list
export PATH="/Users/runner/miniconda3/envs/opengate_core/bin/:$PATH"

if [[ ${MATRIX_OS} == "macos-15-intel" ]]; then
    conda install conda-forge::qt6-main conda-forge::qt6-3d

    export QT_PLUGIN_DIR="/Users/runner/miniconda3/envs/opengate_core/lib/qt6/plugins"
    export LDFLAGS="-L/usr/local/opt/llvm/lib"
    export CPPFLAGS="-I/usr/local/opt/llvm/include -fopenmp"
else
    brew install qt
    export QT_PLUGIN_DIR=$(qtpaths6 --plugin-dir)
    export LDFLAGS="-L/usr/local/opt/llvm/lib"
    export CPPFLAGS="-I/usr/local/opt/llvm/include -fopenmp"
fi

echo "QT_PLUGIN_DIR is $QT_PLUGIN_DIR"
pip install wget colored setuptools
# install cibuildwheel (>= 4.2 builds CPython 3.15, i.e. cp315)
pip install cibuildwheel==4.3.5

# Geant4 and ITK are installed in $HOME/software/install, the only folder cached
# by the build action (not the sources and build trees)
G4_PREFIX=$HOME/software/install/geant4
ITK_PREFIX=$HOME/software/install/itk
mkdir -p $HOME/software
if [ "${MATRIX_CACHE}" != 'true' ]; then
    cd $HOME/software
    mkdir geant4
    cd geant4
    mkdir src bin data
    git clone --branch $GEANT4_VERSION https://github.com/Geant4/geant4.git --depth 1 src
    cd bin
    cmake -DCMAKE_INSTALL_PREFIX=$G4_PREFIX \
          -DCMAKE_CXX_FLAGS=-std=c++17 \
          -DGEANT4_INSTALL_DATA=OFF \
          -DGEANT4_USE_QT=ON \
          -DGEANT4_USE_OPENGL_X11=OFF \
          -DGEANT4_USE_QT_QT6=ON \
          -DGEANT4_USE_SYSTEM_EXPAT=OFF \
          -DGEANT4_BUILD_MULTITHREADED=ON \
          -DGEANT4_USE_GDML=ON \
          ../src
    make -j4 install
    cd $HOME/software
    mkdir itk
    cd itk
    mkdir src bin
    git clone --branch $ITK_VERSION https://github.com/InsightSoftwareConsortium/ITK.git --depth 1 src
    cd bin
    cmake -DCMAKE_INSTALL_PREFIX=$ITK_PREFIX \
          -DCMAKE_CXX_FLAGS=-std=c++17 \
          -DBUILD_TESTING=OFF \
          -DITK_USE_FFTWD=ON \
          -DITK_USE_FFTWF=ON \
          -DITK_USE_SYSTEM_FFTW:BOOL=ON \
          ../src
    make -j4 install
fi
cd $GITHUB_WORKSPACE
source $G4_PREFIX/share/Geant4/geant4make/geant4make.sh
# setup.py passes G4INSTALL as Geant4_DIR: the folder of Geant4Config.cmake
export G4INSTALL=$G4_PREFIX/lib/cmake/Geant4
# compile opengate_core with ccache (not Geant4 and ITK above): the cache folder
# is saved and restored by the build action. cmake reads the launcher from the
# environment.
export CCACHE_DIR=$HOME/.ccache
export CCACHE_MAXSIZE=1G
export CCACHE_BASEDIR=$GITHUB_WORKSPACE
export CCACHE_COMPILERCHECK=content
export CMAKE_CXX_COMPILER_LAUNCHER=ccache
export CMAKE_C_COMPILER_LAUNCHER=ccache
ccache --zero-stats
export CMAKE_PREFIX_PATH=$G4_PREFIX:$ITK_PREFIX:${CMAKE_PREFIX_PATH}
cp VERSION core/VERSION
cd core

mkdir opengate_core/plugins
cp -r $QT_PLUGIN_DIR/platforms/* opengate_core/plugins/
cp -r $QT_PLUGIN_DIR/imageformats/* opengate_core/plugins/

export CIBW_BUILD_FRONTEND="build"
export CIBW_PLATFORM="macos"
export CIBW_SKIP="*t*"
export MACOSX_DEPLOYMENT_TARGET=15.0
export CIBW_BEFORE_BUILD="pip install cmake colored"

if [[ ${MATRIX_OS} == "macos-15-intel" ]]; then
    export DYLD_LIBRARY_PATH=$G4_PREFIX/lib:/Users/runner/miniconda3/envs/opengate_core/lib/qt6/plugins/platforms:/opt/X11/lib/:$DYLD_LIBRARY_PATH:/Users/runner/miniconda3/envs/opengate_core/lib
    export CIBW_ARCHS_MACOS="x86_64"
else
    export DYLD_LIBRARY_PATH=$G4_PREFIX/lib:/opt/homebrew/share/qt/plugins/platforms/:/opt/X11/lib/:$DYLD_LIBRARY_PATH:/opt/homebrew/lib
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
elif [[ ${MATRIX_PYTHON_VERSION} == "3.15" ]]; then
  export CIBW_BUILD="cp315-*"
fi

python -m cibuildwheel --output-dir dist
ccache --show-stats --verbose || true
# delocate copies QtCore out of its framework bundle, which makes Qt crash at
# start-up with pip installed wheels: put it back in a framework bundle
python $GITHUB_WORKSPACE/.github/workflows/actions_build/fix_macos_qt_framework.py dist/*.whl
cd dist
if [[ ${MATRIX_OS} == "macos-15-intel" ]]; then
    find . -name '*whl' -exec bash -c ' mv $0 ${0/macosx_15_0/macosx_10_9}' {} \;
fi
cd ../..
mv core/dist .

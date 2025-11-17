#!/bin/bash
set -e

source $GITHUB_WORKSPACE/env_dump.txt
brew install python@3.12 || true
brew link --overwrite python@3.12
#brew update
#rm -rf /usr/local/bin/python3.1*-config /usr/local/bin/2to3-3.1* /usr/local/bin/idle3.1* /usr/local/bin/pydoc3.1* /usr/local/bin/python3.1*
#rm -rf /usr/local/bin/python3-config /usr/local/bin/2to3 /usr/local/bin/idle3 /usr/local/bin/pydoc3 /usr/local/bin/python3
brew install --force --verbose --overwrite \
             ccache \
             fftw \
             libomp \
             xquartz \
             xerces-c \
             wget  || true
brew uninstall --ignore-dependencies libxext
brew uninstall --ignore-dependencies libx11
export LDFLAGS="-L/usr/local/opt/llvm/lib"
export CPPFLAGS="-I/usr/local/opt/llvm/include -fopenmp"
conda info
conda list
which python
python --version
export PATH="/usr/local/miniconda/envs/opengate_core/bin/:$PATH"
pip install wget colored
pip install wheel delocate
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
python3 setup.py sdist bdist_wheel
ls dist
if [[ ${MATRIX_OS} == "macos-15-intel" ]]; then
    export DYLD_LIBRARY_PATH=$HOME/software/geant4/bin/BuildProducts/lib:/Users/runner/miniconda3/envs/opengate_core/lib/qt6/plugins/platforms:/opt/X11/lib/:$DYLD_LIBRARY_PATH:/Users/runner/miniconda3/envs/opengate_core/lib
else
    export DYLD_LIBRARY_PATH=$HOME/software/geant4/bin/BuildProducts/lib:/opt/homebrew/share/qt/plugins/platforms/:/opt/X11/lib/:$DYLD_LIBRARY_PATH:/opt/homebrew/lib
    python -c "import os,delocate; print(os.path.join(os.path.dirname(delocate.__file__), 'tools.py'));quit()" | xargs -I{} sed -i."" "s/first, /input.pop('i386',None); first, /g" {}
fi
delocate-listdeps --all dist/*.whl
delocate-wheel -w fixed_wheels -v dist/*.whl
rm -rf dist
ls fixed_wheels
delocate-listdeps --all fixed_wheels/*.whl
mv fixed_wheels dist
cd dist
if [[ ${MATRIX_OS} == "macos-15-intel" ]]; then
    find . -name '*whl' -exec bash -c ' mv $0 ${0/macosx_15_0/macosx_10_9}' {} \;
fi
cd ../..
mv core/dist .
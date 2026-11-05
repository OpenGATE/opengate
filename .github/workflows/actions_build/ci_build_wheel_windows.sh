#!/bin/bash
set -e

source $GITHUB_WORKSPACE/env_dump.txt
source $CONDA/Scripts/activate opengate_core
conda info
conda install cmake==4.2.3
cmake --version
conda list
which python
python --version
export PATH="/usr/local/miniconda/envs/opengate_core/bin/:$PATH"
pip install wget colored delvewheel

pip install cibuildwheel==3.4.0

# For windows 2025, Need to add the certifi CA bundle to avoid SSL errors when downloading dependencies during the build. This is a workaround for cibuildwheel which does not handle this properly on Windows.
python - << 'EOF'
import certifi, shutil, os
dst = os.path.expanduser(r"C:\certifi-ca.pem")
shutil.copy(certifi.where(), dst)
print("Installed CA bundle at", dst)
EOF
export SSL_CERT_FILE="C:\certifi-ca.pem"
export REQUESTS_CA_BUNDLE="C:\certifi-ca.pem"

which pip
which cmake
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
# compile opengate_core with ccache (not Geant4 and ITK above): Ninja instead of
# MSBuild (which does not support ccache), Release (setup.py sets the build type
# for the other OS only; cmake reads it from the environment), the MSVC
# environment comes from the build action. The cache folder is saved and
# restored by the build action.
CCACHE_VERSION=4.11.3
mkdir -p $HOME/.ccache $HOME/ccache_bin
curl -sSL --retry 3 -o $HOME/ccache_bin/ccache.zip https://github.com/ccache/ccache/releases/download/v${CCACHE_VERSION}/ccache-${CCACHE_VERSION}-windows-x86_64.zip
unzip -q -j -o $HOME/ccache_bin/ccache.zip "*/ccache.exe" -d $HOME/ccache_bin
conda install -y ninja
export CCACHE_DIR=$(cygpath -w $HOME/.ccache)
export CCACHE_MAXSIZE=1G
export CCACHE_BASEDIR=$(cygpath -w $GITHUB_WORKSPACE)
export CCACHE_COMPILERCHECK=content
export CMAKE_GENERATOR=Ninja
export CMAKE_BUILD_TYPE=Release
export CMAKE_CXX_COMPILER_LAUNCHER=$(cygpath -m $HOME/ccache_bin/ccache.exe)
export CMAKE_C_COMPILER_LAUNCHER=$(cygpath -m $HOME/ccache_bin/ccache.exe)
which cl ninja link || true
$HOME/ccache_bin/ccache.exe --zero-stats
export CMAKE_PREFIX_PATH=$HOME/software/geant4/bin:$HOME/software/itk/bin/:${CMAKE_PREFIX_PATH}
cp VERSION core/VERSION
cd core
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
echo ${MATRIX_OS}
if [[ ${MATRIX_OS} == "windows-11-arm" ]]; then
    export CIBW_ARCHS="ARM64"
else
    export CIBW_ARCHS="AMD64"
fi
export CIBW_BUILD_FRONTEND="build"
export CIBW_SKIP="*t*"
export CIBW_PLATFORM="windows"
find $HOME/software/geant4/bin/ -iname "*.dll"
ls $HOME/software/geant4/bin/BuildProducts/Release/bin
ls $HOME/software/geant4/bin/BuildProducts/Release/lib/

# use delvewheel on windows
export CIBW_BEFORE_BUILD_WINDOWS="pip install colored"
export CIBW_REPAIR_WHEEL_COMMAND_WINDOWS=''
python -m cibuildwheel --output-dir dist
$HOME/ccache_bin/ccache.exe --show-stats --verbose || true

cd ..
mkdir core/dist2
delvewheel repair -w core/dist2 core/dist/*.whl --add-path $HOME/software/geant4/bin/BuildProducts/Release/bin -vv

ls core/dist2
mv core/dist2 dist

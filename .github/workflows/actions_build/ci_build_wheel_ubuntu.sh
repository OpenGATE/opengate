#!/bin/bash
set -e

source $GITHUB_WORKSPACE/env_dump.txt

pip install wget colored setuptools
pip install cibuildwheel==3.4.0

# Setup the environment for the build
if [ ${MATRIX_OS} == "ubuntu-24.04-arm" ]; then
  export ARMDOCKER="_arm64"
  export CIBW_ARCHS="aarch64"
  export CIBW_MANYLINUX_AARCH64_IMAGE=tbaudier/opengate_core:${GEANT4_VERSION}$ARMDOCKER
else
  export CIBW_ARCHS="x86_64"
  export CIBW_MANYLINUX_X86_64_IMAGE=tbaudier/opengate_core:${GEANT4_VERSION}
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
export CIBW_PLATFORM="linux"
export CIBW_BUILD_FRONTEND="build"
export CIBW_SKIP="*-musllinux_* *t*"
export CIBW_BEFORE_BUILD='
pip install colored &&
mkdir -p opengate_core/plugins &&
export QT_PLUGIN_DIR=$(qtpaths6 --plugin-dir) &&
cp -r -n $QT_PLUGIN_DIR/platforms/* opengate_core/plugins/ &&
cp -r -n $QT_PLUGIN_DIR/imageformats opengate_core/plugins/ &&
cp -r -n $QT_PLUGIN_DIR/xcbglintegrations opengate_core/plugins/ &&
source /software/geant4/bin/geant4make.sh &&
. /opt/rh/gcc-toolset-14/enable
'

# expose external libraries to build environment
export CIBW_ENVIRONMENT='
CMAKE_PREFIX_PATH=/software/geant4/bin:/software/itk/bin/
Geant4_DIR=/software/geant4/lib/cmake/Geant4
ITK_DIR=/software/itk/lib/cmake/ITK
LD_LIBRARY_PATH=/software/geant4/lib:/software/itk/lib
'

# Do not bundle the OpenGL dispatch libraries (libglvnd) in the wheel. Geant4's
# OpenGL driver links the system libGL.so.1, which uses the system libGLX and
# libGLdispatch; bundled copies of them (used by Qt) put a second, private
# OpenGL dispatch layer in the process, a known cause of failing OpenGL
# windows. libGLX and libGLdispatch come with libGL.so.1 (already required), so
# they are taken from the system; libEGL and libOpenGL, not always installed,
# stay bundled but use the system libGLdispatch.
# For the same reason, libxcb and libX11-xcb are not bundled: libX11.so.6 is
# always taken from the system (manylinux policy) and uses the system libxcb,
# while Qt's xcb plugin used the bundled libxcb: the X connection created by one
# libxcb was used by the other, and Qt crashed when starting (segfault in
# xcb_send_request). Both come with libX11 on any X11 desktop. The other xcb
# libraries (xcb-cursor, xcb-icccm...) stay bundled and use the system libxcb.
export CIBW_REPAIR_WHEEL_COMMAND_LINUX='auditwheel repair --exclude libGLX.so.0 --exclude libGLdispatch.so.0 --exclude libxcb.so.1 --exclude libX11-xcb.so.1 -w {dest_dir} {wheel}'

# The xcbglintegrations plugins (GLX, EGL) are needed by the xcb platform
# plugin to create OpenGL contexts: without them, the Qt window opens but stays
# empty ("neither GLX nor EGL are enabled"). Qt finds them in QT_PLUGIN_PATH,
# set by opengate_core (qt5Setup.py).

# Run the build in custom docker
cp VERSION core/VERSION
cd core
python -m cibuildwheel --output-dir dist
mkdir -p $GITHUB_WORKSPACE/dist
mv dist/*.whl $GITHUB_WORKSPACE/dist/
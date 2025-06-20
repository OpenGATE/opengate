#!/bin/bash

set -e -x
echo ${PYTHONFOLDER}
cd /home/core/
cd /software/cmake
rm -rf *
if [ "$(uname -m)" = "aarch64" ]; then
    wget https://github.com/Kitware/CMake/releases/download/v3.31.8/cmake-3.31.8-linux-aarch64.tar.gz
    tar xzvf cmake-3.31.8-linux-aarch64.tar.gz
    export PATH=/software/cmake/cmake-3.31.8-linux-aarch64/bin/:${PATH}
else
    wget https://github.com/Kitware/CMake/releases/download/v3.31.8/cmake-3.31.8-linux-x86_64.tar.gz
    tar xzvf cmake-3.31.8-linux-x86_64.tar.gz
    export PATH=/software/cmake/cmake-3.31.8-Linux-x86_64/bin/:${PATH}
fi
cd /home/core/
source /software/geant4/bin/geant4make.sh
export CMAKE_PREFIX_PATH=/software/geant4/bin:/software/itk/bin/:${CMAKE_PREFIX_PATH}
. /opt/rh/gcc-toolset-14/enable
mkdir opengate_core/plugins
cp -r /lib64/qt6/plugins/platforms/* opengate_core/plugins/
cp -r /lib64/qt6/plugins/imageformats opengate_core/plugins/
/opt/python/${PYTHONFOLDER}/bin/pip install wget colored setuptools
/opt/python/${PYTHONFOLDER}/bin/python setup.py sdist bdist_wheel
archi=`uname -m`
if [ "$(uname -m)" = "aarch64" ]; then
  auditwheel repair /home/core/dist/*.whl -w /software/wheelhouse/ --plat "manylinux_2_34_aarch64"
else
  auditwheel repair /home/core/dist/*.whl -w /software/wheelhouse/ --plat "manylinux_2_34_x86_64"
fi
cp -r /software/wheelhouse /home/
#/opt/python/${PYTHONFOLDER}/bin/pip install twine
#/opt/python/${PYTHONFOLDER}/bin/twine upload --repository-url https://test.pypi.org/legacy/ wheelhouse/*manylinux2014*.whl

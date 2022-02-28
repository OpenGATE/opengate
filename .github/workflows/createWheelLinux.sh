#!/bin/bash

set -e -x
echo ${PYTHONFOLDER}
#git clone --recurse-submodules https://github.com/tbaudier/gam_g4.git gam_g4
cd /home/
#git pull --recurse-submodules
export PATH=/software/cmake/cmake-3.18.2-Linux-x86_64/bin/:${PATH}
source /software/geant4/bin/geant4make.sh
export CMAKE_PREFIX_PATH=/software/geant4/bin:/software/itk/bin/:${CMAKE_PREFIX_PATH}
mkdir gam_g4/plugins
cp -r /lib64/qt5/plugins/platforms gam_g4/plugins
cp -r /lib64/qt5/plugins/imageformats gam_g4/plugins
/opt/python/${PYTHONFOLDER}/bin/pip install wget colored
/opt/python/${PYTHONFOLDER}/bin/python setup.py sdist bdist_wheel
auditwheel repair /home/dist/*.whl -w /software/wheelhouse/ --plat "manylinux2014_x86_64"
cp -r /software/wheelhouse /home/
#/opt/python/${PYTHONFOLDER}/bin/pip install twine
#/opt/python/${PYTHONFOLDER}/bin/twine upload --repository-url https://test.pypi.org/legacy/ wheelhouse/*manylinux2014*.whl


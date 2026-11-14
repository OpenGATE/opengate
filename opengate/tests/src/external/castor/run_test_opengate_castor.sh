#! /bin/bash

#Instal opengate wheels
cd /home/.github/workflows
/opt/python/cp312-cp312/bin/pip install opengate_core-*.whl
/opt/python/cp312-cp312/bin/pip install opengate-*.whl
cd /opt/_internal/cpython-3.12.12/lib/python3.12/site-packages/opengate/tests/src/external/castor
/opt/python/cp312-cp312/bin/python test096_pet_castor.py
/opt/python/cp312-cp312/bin/python test096_pet_castor_ref.py
/opt/python/cp312-cp312/bin/python test096_pet_castor_coinc.py
cd /opt/_internal/cpython-3.12.12/lib/python3.12/site-packages/opengate/tests/output/test096_pet_castor_interface

#Convert Gate root output to Castor
export PATH=/software/castor/bin/:$PATH
castor-GATERootToCastor -vb 2 -i coincidences.root -o test_gatev10 -js castor_config.json -s "PET_GATEv10_TEST" -t -geo

#Reonstruction with castor
castor-recon -vb 2 -df test_gatev10_df.Cdh -fout reco_test_gatev10 -oit -1 -it 10:1 -dim 128,128,40 -vox 3,3,3 -th 0 -fov-out 98. -slice-out 2



#!/bin/bash
cd /opt/python/cp312-cp312/lib/python3.12/site-packages/opengate/tests/src/advanced_tests/linacs/
export PATH=/opt/python/cp312-cp312/bin:$PATH
python run_vmat_mc.py --json_name data_advanced_test_linac/header.json
python normalize_dose.py --path data_advanced_test_linac
python comparison_deposited_dose_mc_tps.py --path data_advanced_test_linac --path_output output > output/output.log 2>&1
